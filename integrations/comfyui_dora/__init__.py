"""ai-toolkit DoRA (`.magnitude`) model loader for ComfyUI — EXPERIMENTAL, explicit only.

The installed ComfyUI parser loads only the A/B tensors of ai-toolkit DoRA files and drops
`.magnitude` (INCOMPLETE_ADAPTER). Its own DoRA path is not a substitute: for an output-axis
scale it normalizes by the *base* weight and applies strength outside the decomposition, while
ai-toolkit normalizes by the *adapted* weight with the multiplier inside.

This node consumes the file's A/B/magnitude triples unchanged (no key renaming, no weight file
rewrite) and patches the model in memory through ComfyUI's WeightAdapterBase interface:

    delta   = B @ A
    adapted = W + m * delta
    W'      = adapted * (magnitude / ||adapted||_row) + m * (r - 1) * delta

m is the node strength (ai-toolkit multiplier) and r = alpha/rank is an explicit hypothesis input
(the file carries no alpha; the pinned ai-toolkit 0.12.9 PEFT export path implies r = 1, which is
source-supported, not authored evidence). At r = 1 this is the dense merge of the pinned ai-toolkit
forward. Every triple must map to a model weight and every tensor must be consumed, otherwise the
node fails instead of loading a partial adapter.
"""

NODE_NAME = 'AssetpipeAIToolkitDoRALoader'
TRIPLE_SUFFIXES = ('.lora_A.weight', '.lora_B.weight', '.magnitude')


def aitoolkit_dora_weight(weight, down, up, magnitude, *, strength, alpha_over_rank):
    """Merged ai-toolkit DoRA weight for a 2D (out, in) linear weight; caller chooses dtype/device."""
    import torch

    if weight.ndim != 2 or down.ndim != 2 or up.ndim != 2 or magnitude.ndim != 1:
        raise ValueError('DORA_2D_LINEAR_REQUIRED')
    if (down.shape[1] != weight.shape[1] or up.shape[0] != weight.shape[0]
            or up.shape[1] != down.shape[0] or magnitude.shape[0] != weight.shape[0]):
        raise ValueError('DORA_OUTPUT_AXIS_SHAPES_REQUIRED')
    if not alpha_over_rank > 0:
        raise ValueError('DORA_EXPLICIT_POSITIVE_ALPHA_RATIO_REQUIRED')
    if strength == 0:
        return weight.clone()
    delta = up @ down
    adapted = weight + strength * delta
    norm = torch.linalg.vector_norm(adapted, dim=1)
    if not torch.isfinite(norm).all() or (norm == 0).any():
        raise ValueError('DORA_ZERO_OR_NONFINITE_ADAPTED_NORM')
    return adapted * (magnitude / norm)[:, None] + strength * (alpha_over_rank - 1) * delta


def group_triples(state_dict):
    """Group an ai-toolkit DoRA state dict into {stem: (A, B, magnitude)}; reject anything else."""
    stems = {}
    for key in state_dict:
        suffix = next((s for s in TRIPLE_SUFFIXES if key.endswith(s)), None)
        if suffix is None:
            raise ValueError(f'DORA_UNEXPECTED_KEY: {key}')
        stems.setdefault(key[:-len(suffix)], {})[suffix] = state_dict[key]
    incomplete = sorted(stem for stem, parts in stems.items() if len(parts) != 3)
    if incomplete:
        raise ValueError(f'DORA_INCOMPLETE_TRIPLES: {incomplete[:3]}')
    return {stem: tuple(parts[s] for s in TRIPLE_SUFFIXES) for stem, parts in stems.items()}


def _adapter_class():
    import torch
    import comfy.model_management
    from comfy.weight_adapter.base import WeightAdapterBase

    class AIToolkitDoRAAdapter(WeightAdapterBase):
        name = 'aitoolkit_dora'

        # ComfyUI rebuilds adapters as type(a)(loaded_keys, weights) when prefetching for dynamic
        # VRAM (comfy.lora.prefetch_prepared_value), moving only tensors inside `weights`. The
        # alpha/rank ratio therefore travels as the last, non-tensor element of `weights`.
        def __init__(self, loaded_keys, weights):
            self.loaded_keys = loaded_keys
            self.weights = weights

        def calculate_weight(self, weight, key, strength, strength_model, offset, function,
                             intermediate_dtype=torch.float32, original_weight=None):
            if offset is not None:
                raise ValueError(f'DORA_OFFSET_UNSUPPORTED: {key}')
            *tensors, alpha_over_rank = self.weights
            down, up, magnitude = (comfy.model_management.cast_to_device(t, weight.device, intermediate_dtype)
                                   for t in tensors)
            base = weight.to(intermediate_dtype)
            merged = aitoolkit_dora_weight(base, down, up, magnitude, strength=strength,
                                           alpha_over_rank=alpha_over_rank)
            apply = function if function is not None else (lambda value: value)
            weight += apply((merged - base).type(weight.dtype))
            return weight

    return AIToolkitDoRAAdapter


def build_patches(model, state_dict, alpha_over_rank):
    """Map every triple to a model weight key; return {model_key: adapter}."""
    import comfy.lora

    triples = group_triples(state_dict)
    key_map = comfy.lora.model_lora_keys_unet(model.model, {})
    model_sd = model.model.state_dict()
    adapter = _adapter_class()
    patches, missing = {}, []
    for stem, (down, up, magnitude) in sorted(triples.items()):
        target = key_map.get(stem)
        if not isinstance(target, str) or target not in model_sd:
            missing.append(stem)
            continue
        if tuple(model_sd[target].shape) != (up.shape[0], down.shape[1]) or magnitude.shape[0] != up.shape[0]:
            raise ValueError(f'DORA_SHAPE_MISMATCH: {stem} -> {target}')
        patches[target] = adapter({f'{stem}{s}' for s in TRIPLE_SUFFIXES}, (down, up, magnitude, float(alpha_over_rank)))
    if missing:
        raise ValueError(f'DORA_UNMAPPED_TARGETS: {len(missing)} e.g. {missing[:3]}')
    return patches


class AssetpipeAIToolkitDoRALoader:
    CATEGORY = 'loaders/assetpipe'
    RETURN_TYPES = ('MODEL',)
    FUNCTION = 'load'
    DESCRIPTION = ('EXPERIMENTAL: applies ai-toolkit DoRA files including .magnitude '
                   '(adapted-weight norm, strength inside). alpha_over_rank is an explicit hypothesis.')

    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths
        return {'required': {
            'model': ('MODEL',),
            'lora_name': (folder_paths.get_filename_list('loras'),),
            'strength': ('FLOAT', {'default': 1.0, 'min': 0.0, 'max': 1.0, 'step': 0.01}),
            'alpha_over_rank': ('FLOAT', {'default': 1.0, 'min': 0.001, 'max': 16.0, 'step': 0.001,
                                          'tooltip': 'Explicit hypothesis; the file stores no alpha.'}),
        }}

    def load(self, model, lora_name, strength, alpha_over_rank):
        import logging
        import comfy.utils
        import folder_paths

        state_dict = comfy.utils.load_torch_file(folder_paths.get_full_path_or_raise('loras', lora_name), safe_load=True)
        patches = build_patches(model, state_dict, alpha_over_rank)
        patched = model.clone()
        applied = patched.add_patches(patches, strength)
        if len(applied) != len(patches):
            raise ValueError(f'DORA_PATCHES_NOT_APPLIED: {len(patches) - len(applied)}')
        logging.info('[assetpipe DoRA] %s: %d targets, %d tensors consumed, strength %s, alpha/rank %s',
                     lora_name, len(patches), len(state_dict), strength, alpha_over_rank)
        return (patched,)


NODE_CLASS_MAPPINGS = {NODE_NAME: AssetpipeAIToolkitDoRALoader}
NODE_DISPLAY_NAME_MAPPINGS = {NODE_NAME: 'Assetpipe ai-toolkit DoRA Loader (experimental)'}

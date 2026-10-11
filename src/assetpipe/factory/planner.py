"""Offline plans only. No provider imports, dispatch, allocations or reservations."""
from copy import deepcopy
from pathlib import Path
from ..brief import make, validate as validate_brief
from ..paths import RootResolver
from .contracts import validate
from .provenance import Sources

def plan(request, root, *, resolver=None, base=None):
    request = validate(request)
    root = Path(root).resolve(strict=True)
    resolver = resolver or RootResolver([root], base=base or root)
    sources = Sources(resolver)
    base = Path(base or resolver.base)
    line, mode, source = request['factory_line'], request['output_mode'], request['source']
    static_class = {'NONPIXEL':'NONPIXEL_IMAGE', 'PIXEL64':'PIXEL_STATIC', 'SFX':'SFX', 'REFERENCE_MOTION':None}[line]
    images, parent = [], None
    if source['kind'] == 'GENERATE':
        path, _, brief = sources.document(source['brief_ref'], base=base)
        # Resolve Brief references without changing identity, prompt or model selection.
        from ..brief import load
        brief = load(path)
        if brief['asset_id'] != request['asset_id'] or brief.get('project_id','default') != request['project_id'] or brief['output_class'] != static_class:
            raise ValueError('FACTORY_BRIEF_MISMATCH: project, asset or output class differs')
        if line == 'PIXEL64' and brief['constraints']['resolution'] != [64,64]:
            raise ValueError('FACTORY_BRIEF_MISMATCH: PIXEL64 needs explicit 64x64 logical output')
        if line == 'SFX' and brief.get('audio',{}).get('duration_seconds') != request['audio']['duration_seconds']:
            raise ValueError('FACTORY_BRIEF_MISMATCH: audio duration differs')
    else:
        images = [sources.image(item, base) for item in source['images']]
        if len({i['path'] for i in images}) != len(images) or len({i['sha256'] for i in images}) != len(images):
            raise ValueError('FACTORY_SOURCE_INVALID: duplicate physical image or content')
        if line == 'PIXEL64' and any(i['size'] != [64,64] for i in images):
            raise ValueError('FACTORY_SOURCE_INVALID: PIXEL64 source must be 64x64')
        if source['kind'] == 'EXISTING_RUN':
            path, sha, manifest = sources.document(source['manifest_ref'],source['manifest_sha256'],base)
            if manifest.get('project_id',manifest.get('asset_brief',{}).get('project_id','default')) != request['project_id']:
                raise ValueError('FACTORY_PARENT_MISMATCH: project differs')
            allowed_classes = [static_class] if static_class else ['NONPIXEL_IMAGE','PIXEL_STATIC']
            if manifest.get('output_class') not in allowed_classes:
                raise ValueError('FACTORY_PARENT_MISMATCH: parent must be a compatible still run')
            outputs = manifest.get('outputs',[])
            paths = [v if isinstance(v,str) else v.get('path') for v in outputs if isinstance(v,(str,dict))]
            resolved = {str(sources.file(p,path.parent)) for p in paths if p}
            if any(i['path'] not in resolved for i in images):
                raise ValueError('FACTORY_PARENT_MISMATCH: selected image is not a recorded output')
            brief = validate_brief(deepcopy(manifest.get('asset_brief', {})))
            if brief['output_class'] != manifest['output_class'] or brief.get('project_id','default') != request['project_id']:
                raise ValueError('FACTORY_PARENT_MISMATCH: parent Brief differs from manifest')
            if line == 'PIXEL64' and brief['constraints']['resolution'] != [64,64]:
                raise ValueError('FACTORY_PARENT_MISMATCH: parent logical output must be 64x64')
            parent = {'manifest_path': str(path), 'manifest_sha256': sha,
                      'run_id': manifest.get('run_id'), 'asset_id': manifest.get('asset_id'),
                      'review_state': 'NOT_EVALUATED', 'mutation_allowed': False}
        if not parent:
            # External references do not establish canon or approval.
            brief = make(asset_id=request['asset_id'], output_class='NONPIXEL_ANIMATION',
                         reference=images[0]['path'], action=request['motion']['action'])
            brief['project_id'] = request['project_id']
            brief['unspecified_elements'].append('source-backed canonical traits and project SOT')
            validate_brief(brief)
    tasks = []
    if source['kind'] == 'GENERATE':
        tasks.append({'id': 'source', 'kind': 'AUDIO' if line == 'SFX' else 'IMAGE',
                      'pipeline': {'NONPIXEL':'nonpixel_image','PIXEL64':'pixel_static','SFX':'sfx'}[line],
                      'output_class': static_class, 'depends_on': [], 'new_run': True})
    else:
        tasks.append({'id': 'source', 'kind': 'EXISTING_IMAGE', 'pipeline': 'read_only_source',
                      'output_class': static_class or (manifest.get('output_class') if parent else 'NONPIXEL_IMAGE'),
                      'depends_on': [], 'new_run': False})
    if mode == 'IMAGE_TO_SPRITE':
        for id_,kind,dependency,pipeline in [('motion','VIDEO','source','shared_motion'),('frames','FRAMES','motion','frame_extraction'),('sprites','SPRITES','frames','sprite_export')]:
            tasks.append({'id':id_,'kind':kind,'pipeline':pipeline,'depends_on':[dependency],
                          'new_run':kind == 'VIDEO','run_owner':'motion'})
        tasks[1]['source_binding'] = {
            'mode':'GENERATED_SOURCE_RECEIPT' if source['kind'] == 'GENERATE' else 'HASHED_SOURCE_RECEIPT',
            'parent_manifest_sha256':parent['manifest_sha256'] if parent else None,
            'image_sha256':[i['sha256'] for i in images], 'required_before_dispatch':True}
    mapped_class = ('PIXEL_ANIMATION' if line == 'PIXEL64' else 'NONPIXEL_ANIMATION') if mode == 'IMAGE_TO_SPRITE' else static_class
    from ..audio.sfx import clip_contract
    return {'factory_contract_version':1, 'status':'OFFLINE_CONTRACT_PASS', 'execution_status':'NOT_IMPLEMENTED_FACTORY_DISPATCH',
            'factory_line':line,'output_mode':mode,'project_id':request['project_id'],'asset_id':request['asset_id'],
            'mapped_output_class':mapped_class,'source_brief':deepcopy(brief),'tasks':tasks,'parent':parent,'images':images,
            'source_documents':sources.receipts, 'motion_contract':deepcopy(request.get('motion')),
            'audio_contract':clip_contract(request['audio'],request['asset_id']) if line == 'SFX' else None,
            'authorization_evaluated':False,'dispatches':0,'budget_reservations':0,'provider_allocations':0,
            'retry':'NONE','fallback':'NONE','game_ready':False,'review_state':'NOT_EVALUATED',
            'remaining_gates':(['BLOCKED_BACKEND_NOT_VERIFIED','REFERENCE_CONTRACT_CAPABILITY_CHECK','SPRITE_QA','HUMAN_MOTION_REVIEW'] if mode == 'IMAGE_TO_SPRITE' else []) +
                              ['EXPLICIT_GENERATION_AUTHORIZATION_WHEN_NEEDED','EXISTING_ROUTE_AND_QA_GATES','HUMAN_REVIEW'],
            'source_and_motion_runs_independent':True}

def plan_file(request_path, root, *, allowed_roots=None):
    resolver = RootResolver(allowed_roots if allowed_roots is not None else [root], base=root)
    sources = Sources(resolver)
    path, sha, request = sources.document(request_path)
    result = plan(request,root,resolver=resolver,base=path.parent)
    result['request'] = {'path':str(path),'sha256':sha}
    return result

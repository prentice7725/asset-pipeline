"""Configured filesystem boundary shared by adapters and provenance consumers."""
import json
import ntpath
import os
from pathlib import Path, PureWindowsPath

ROOTS_ENV = 'ASSETPIPE_ALLOWED_ROOTS'


def _reserved_windows_name(name):
    if hasattr(ntpath, 'isreserved'):
        return ntpath.isreserved(name)
    return PureWindowsPath(name).is_reserved()  # Python 3.11/3.12 compatibility.


def _namespace_key(path):
    """Compare safe DOS/UNC aliases only after filesystem resolution.

    Windows realpath can retain its extended prefix during directory creation.
    Do not reinterpret device namespaces or names whose Win32 meaning differs.
    """
    if not isinstance(path, PureWindowsPath):
        return path
    text = str(path)
    if text[:8].upper() == '\\\\?\\UNC\\':
        plain = '\\\\' + text[8:]
    elif (text.startswith('\\\\?\\') and len(text) >= 7 and text[4].isascii()
          and text[4].isalpha() and text[5:7] == ':\\'):
        plain = text[4:]
    else:
        return path
    key = type(path)(plain)
    if not key.is_absolute():
        return path
    parts = key.parts[1:]
    if key.drive.startswith('\\\\'):
        parts += tuple(key.drive[2:].split('\\'))
    if any(part in {'.', '..'} or part.endswith(('.', ' '))
           or _reserved_windows_name(part)
           or any(c in '<>:"/\\|?*' or ord(c) < 32 for c in part) for part in parts):
        return path
    return key


class RootResolver:
    def __init__(self, roots, *, base=None):
        self.roots = tuple(Path(p).resolve(strict=True) for p in roots)
        if not self.roots or any(not p.is_dir() for p in self.roots):
            raise ValueError('Configured roots must be nonempty directories')
        self.base = Path(base or Path.cwd()).resolve()

    def __call__(self, value, *, strict=True):
        if not isinstance(value, (str, Path)) or not str(value) or '\x00' in str(value):
            raise ValueError('Invalid filesystem reference')
        path = (self.base / value).resolve(strict=strict)
        if any(path.is_relative_to(root) for root in self.roots):
            return path
        key = _namespace_key(path)
        for root in self.roots:
            root_key = _namespace_key(root)
            if key.is_relative_to(root_key):
                if root != root_key:
                    # Preserve an explicitly configured extended namespace so
                    # downstream identity/alias guards keep the same spelling.
                    text = str(key)
                    return type(key)('\\\\?\\UNC\\' + text[2:] if text.startswith('\\\\')
                                     else '\\\\?\\' + text)
                return key
        raise ValueError('Path is outside configured roots')

    def environment(self):
        return json.dumps({'roots': [str(p) for p in self.roots], 'base': str(self.base)})


def resolve_path(value, resolver=None, *, strict=True):
    if resolver is None and ROOTS_ENV in os.environ:
        policy = json.loads(os.environ[ROOTS_ENV])
        resolver = RootResolver(policy['roots'], base=policy['base'])
    return resolver(value, strict=strict) if resolver else Path(value).resolve(strict=strict)


def validate_references(value, resolver=None):
    """Check serialized provenance references, including unused candidate rows.

    Missing historical references need not exist, but must still be contained.
    Consumers resolve strictly again immediately before reading.
    """
    scalar = {'source_manifest', 'source_report', 'source_video', 'resolution_report',
              'resolution_review', 'candidate', 'export', 'aseprite_master', 'image',
              'approved_export', 'static_master', 'approval_record', 'motion_reference',
              'selection', 'source_frames', 'path', 'report', 'master', 'sprite_sheet',
              'json_metadata', 'source_path', 'final_path'}
    plural = {'paths', 'references', 'outputs'}
    if isinstance(value, dict):
        for key, item in value.items():
            if (key in scalar or key.endswith('_path')) and isinstance(item, str) and item:
                resolve_path(item, resolver, strict=False)
            elif (key == 'source_notes' and isinstance(item, list)
                  and isinstance(value.get('source'), dict) and value['source'].get('type') == 'DOCUMENTS'):
                for note in item:
                    if isinstance(note, dict) and note.get('source'):
                        resolve_path(note['source'], resolver, strict=False)
            elif key in plural and isinstance(item, list):
                for reference in item:
                    if isinstance(reference, str):
                        resolve_path(reference, resolver, strict=False)
            validate_references(item, resolver)
    elif isinstance(value, list):
        for item in value:
            validate_references(item, resolver)

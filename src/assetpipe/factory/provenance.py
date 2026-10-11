"""Read-only, configured-root validation before any source read or hash."""
import hashlib
import json
from pathlib import Path
from PIL import Image
from ..paths import RootResolver, validate_references

def fingerprint(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

class Sources:
    def __init__(self, resolver):
        if not isinstance(resolver, RootResolver):
            raise ValueError('Factory sources require a configured RootResolver')
        self.resolver = resolver
        self.receipts = []
        self.visited = set()

    def file(self, value, base=None):
        path = self.resolver(Path(base or self.resolver.base) / value)
        if not path.is_file():
            raise ValueError('FACTORY_SOURCE_INVALID: expected a file')
        return path

    def document(self, value, expected=None, base=None):
        path = self.file(value, base)
        sha = fingerprint(path)
        if expected is not None and sha != expected:
            raise ValueError('FACTORY_SOURCE_CHANGED: document hash mismatch')
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('FACTORY_SOURCE_INVALID: expected a JSON object')
        local = RootResolver(self.resolver.roots, base=path.parent)
        validate_references(data, local)
        # Explicit document links are validated recursively, including nested evidence.
        if path not in self.visited:
            self.visited.add(path)
            self.receipts.append({'path': str(path), 'sha256': sha, 'kind': 'DOCUMENT'})
            def follow(value):
                if isinstance(value, dict):
                    for key, item in value.items():
                        if key in {'source_manifest','resolution_report','resolution_review','source_report','approval_record'} and isinstance(item,str) and item:
                            child = self.file(item, path.parent)
                            if child not in self.visited:
                                self.document(str(child))
                        else:
                            follow(item)
                elif isinstance(value, list):
                    for item in value: follow(item)
            follow(data)
        return path, sha, data

    def image(self, item, base):
        path = self.file(item['path'], base)
        sha = fingerprint(path)
        if sha != item['sha256']:
            raise ValueError('FACTORY_SOURCE_CHANGED: image hash mismatch')
        with Image.open(path) as image:
            if image.format not in {'PNG','JPEG','WEBP'}:
                raise ValueError('FACTORY_SOURCE_INVALID: unsupported still image format')
            image.verify()
        with Image.open(path) as image:
            size = list(image.size)
        return {**item, 'path': str(path), 'sha256': sha, 'size': size}

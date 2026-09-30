from ..._ported.aseprite_bridge.runner import build_master, find_aseprite, get_version

class AsepriteProvider:
    def __init__(self, config):
        self.config = config
        self.executable = find_aseprite(config.section('aseprite').get('executable'))
        if self.executable is None:
            raise ValueError('Aseprite executable is unavailable')

    def export(self, frames, output, asset_id, action='static', duration=125):
        get_version(self.executable)
        report = build_master(self.executable, source=frames[0], frames=frames[1:], output_dir=output,
            project_root=self.config.root, character_id=asset_id, tag_name=action,
            frame_duration_ms=duration, timeout=int(self.config.section('aseprite').get('timeout_seconds', 120)))
        if report['status'] != 'PASS':
            raise ValueError('Aseprite integrity gate failed')
        return report

from ..._ported.motion_extractor.extract import extract_motion

def decode_direct_reference(video, output, last_index):
    """Preserve the legacy direct path's FFmpeg RGB decode, not OpenCV conversion."""
    from pathlib import Path
    import shutil
    import subprocess
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise ValueError('Verified direct reference decoding requires FFmpeg on PATH')
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=False)
    command = [ffmpeg, '-v', 'error', '-i', str(video), '-start_number', '0', '-frames:v', str(last_index + 1), str(directory / 'frame_%04d.png')]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise ValueError(f'FFmpeg decode failed: {result.stderr.strip()}')
    version = subprocess.run([ffmpeg, '-version'], capture_output=True, text=True, check=True, timeout=10).stdout.splitlines()[0]
    return {'command': command, 'version': version, 'decoded_count': len(list(directory.glob('frame_*.png')))}

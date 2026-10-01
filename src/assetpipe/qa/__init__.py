"""이미지 후보 공통 QA. 엔진(comfyui, codex_cli, grok_cli)과 무관하게 같은 기준을 적용한다.

QA가 통과해도 후보는 자동 승인되지 않는다. 정본·금지 요소 준수는 사람이 확인해야 하며 보고서에 그 항목을 남긴다.
"""
from PIL import Image
from ..providers.cli_runner import sha256_file

ASPECT_TOLERANCE = 0.03


def basic_image_qa(path, brief, *, external_engine=False):
    """한 장의 이미지를 검사해 보고서를 돌려준다. 실패 사유는 reasons에 담고, 판정은 status에 둔다."""
    report = {'step': 'basic_image_qa', 'status': 'PASS', 'path': str(path), 'reasons': []}
    with Image.open(path) as image:
        image.load()
        size = list(image.size)
        report.update({'resolution': size, 'format': image.format, 'mode': image.mode})
        if image.width < 1 or image.height < 1:
            report['reasons'].append('Invalid image dimensions')
        expected = brief['constraints']['resolution']
        if expected and size != expected:
            report['reasons'].append('Image resolution differs from brief')
        if brief['constraints']['transparency'] is True and image.convert('RGBA').getchannel('A').getextrema()[0] == 255:
            report['reasons'].append('Requested transparent image is fully opaque')
        ratio = (brief.get('prompt_spec') or {}).get('aspectRatio')
        if ratio and external_engine:
            w, h = map(int, ratio.split(':'))
            if abs(size[0] / size[1] - w / h) / (w / h) > ASPECT_TOLERANCE:
                report['reasons'].append('Image aspect ratio differs from PromptSpec aspectRatio')
    if external_engine:
        # 외부 CLI 결과는 해시와 사람 검토 항목까지 보고서에 남긴다.
        report['sha256'] = sha256_file(path)
        report['review_required'] = {'canonical_traits': list(brief['identity']['canonical_traits']),
            'forbidden_elements': list(brief['forbidden_elements']), 'note': 'Not machine-verifiable; human visual review is required'}
    if report['reasons']:
        report['status'] = 'FAIL'
    return report

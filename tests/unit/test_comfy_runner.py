"""ComfyUI 실행기 순서·기록 테스트. 가짜 클라이언트만 쓰며 실제 서버에 요청하지 않는다."""
import json
from pathlib import Path

import pytest

from assetpipe._ported.comfy_bridge import runner
from assetpipe._ported.config import load_config
from assetpipe._ported.errors import ExternalServiceError

ROOT = Path(__file__).resolve().parents[2]


class FakeClient:
    queued = []

    def __init__(self, base_url, **kwargs):
        self.base_url = base_url

    def check_connection(self):
        return {'system': {'comfyui_version': 'fake'}}

    def upload_image(self, path):
        return path.name

    def queue_prompt(self, prompt, client_id):
        FakeClient.queued.append(client_id)
        return 'prompt-1'

    def wait_for_outputs(self, prompt_id, nodes):
        raise OSError('disk full')


@pytest.fixture
def fake(monkeypatch):
    FakeClient.queued = []
    monkeypatch.setattr(runner, 'ComfyClient', FakeClient)
    return load_config(ROOT / 'config/pipeline.yaml')


def test_existing_output_dir_is_rejected_before_queueing(fake, tmp_path):
    (tmp_path / 'out').mkdir()
    with pytest.raises(FileExistsError):
        runner.run_workflow(fake, workflow_name='concept_character', prompt='fox', seed=1, output_dir=tmp_path / 'out')
    assert FakeClient.queued == []


def test_pre_queue_failure_releases_the_empty_output_dir(fake, tmp_path, monkeypatch):
    def refuse(self, prompt, client_id):
        raise ExternalServiceError('queue refused')
    monkeypatch.setattr(FakeClient, 'queue_prompt', refuse)
    with pytest.raises(ExternalServiceError):
        runner.run_workflow(fake, workflow_name='concept_character', prompt='fox', seed=1, output_dir=tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_unexpected_error_after_queue_marks_generation_failed(fake, tmp_path):
    with pytest.raises(OSError):
        runner.run_workflow(fake, workflow_name='concept_character', prompt='fox', seed=1, output_dir=tmp_path / 'out')
    metadata = json.loads((tmp_path / 'out/generation.json').read_text(encoding='utf-8'))
    assert metadata['status'] == 'FAILED' and metadata['prompt_id'] == 'prompt-1' and 'disk full' in metadata['error']


class ScriptedClient(runner.ComfyClient):
    """정해진 순서로 /history와 /queue 응답을 돌려주는 클라이언트."""

    def __init__(self, histories, queues):
        super().__init__('http://127.0.0.1:1', execution_timeout=5, poll_interval=0)
        self.histories, self.queues = list(histories), list(queues)

    def _json(self, path, **kwargs):
        return self.histories.pop(0) if path.startswith('/history/') else self.queues.pop(0)


DONE = {'p1': {'status': {'status_str': 'success', 'completed': True},
               'outputs': {'9': {'images': [{'filename': 'out.png'}]}}}}
EMPTY_QUEUE = {'queue_running': [], 'queue_pending': []}


def test_prompt_dropped_from_queue_fails_without_waiting_for_timeout():
    client = ScriptedClient([{}, {}], [EMPTY_QUEUE])
    with pytest.raises(ExternalServiceError, match='dropped'):
        client.wait_for_outputs('p1', ('9',))


@pytest.mark.parametrize('histories, queues', [
    ([{}, DONE], [{'queue_running': [], 'queue_pending': [[1, 'p1', {}]]}]),  # 대기 중이었다가 끝남
    ([{}, DONE, DONE], [EMPTY_QUEUE]),  # 큐 조회 직전에 끝나 기록에만 있음
])
def test_queued_or_just_finished_prompt_is_collected(histories, queues):
    assert ScriptedClient(histories, queues).wait_for_outputs('p1', ('9',)) == [{'filename': 'out.png'}]

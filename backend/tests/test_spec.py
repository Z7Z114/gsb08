"""行为规格测试：逐条盯住 README「行为规格」的验收点。

这些用例在未修复的实现上应当失败，修复后通过。
"""
import glob
import importlib
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import wave

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def make_wav_bytes(seconds=1.0, rate=8000):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b''.join(struct.pack('<h', 0) for _ in range(int(seconds * rate))))
    return buf.getvalue()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('DATA_DIR', str(tmp_path / 'data'))
    for var in ('OPENAI_API_KEY', 'PYANNOTE_AUTH_TOKEN',
                'EMAIL_USER', 'EMAIL_PASSWORD', 'EMAIL_RECIPIENTS'):
        monkeypatch.delenv(var, raising=False)

    import app as app_module
    import data_store
    importlib.reload(data_store)
    importlib.reload(app_module)

    application = app_module.app
    application.config['TESTING'] = True
    app_module.data_store = data_store.DataStore(data_dir=str(tmp_path / 'data'))
    with application.test_client() as test_client:
        yield test_client


def design_payload(**overrides):
    data = {
        'series_name': '靛蓝秋系列',
        'fabric_type': 'linen',
        'complexity': 'medium',
        'quantity': 10,
        'notes': '首次打样',
    }
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


def post_meeting(client, design_data=None, audio_name='会议.wav'):
    form = {'audio': (io.BytesIO(make_wav_bytes()), audio_name)}
    if design_data is not None:
        form['designData'] = design_data
    return client.post('/api/process-meeting', data=form,
                       content_type='multipart/form-data')


def create_meeting_id(client):
    resp = post_meeting(client, design_payload())
    assert resp.status_code == 200
    return resp.get_json()['meeting_id']


# ---------- A. 请求校验与错误响应 ----------

class TestRequestValidation:
    def test_process_meeting_invalid_design_data_returns_400(self, client):
        resp = post_meeting(client, '这不是JSON')
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_process_meeting_design_data_must_be_object(self, client):
        resp = post_meeting(client, '[1, 2, 3]')
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_process_meeting_missing_audio_returns_400(self, client):
        resp = client.post('/api/process-meeting',
                           data={'designData': design_payload()},
                           content_type='multipart/form-data')
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_process_meeting_invalid_quantity_in_design_data(self, client):
        resp = post_meeting(client, design_payload(quantity=0))
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_cost_calculator_invalid_json_returns_400(self, client):
        resp = client.post('/api/cost-calculator', data='{不是json',
                           content_type='application/json')
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_cost_calculator_non_object_json_returns_400(self, client):
        resp = client.post('/api/cost-calculator', json=[1, 2, 3])
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_send_email_invalid_json_returns_400(self, client):
        meeting_id = create_meeting_id(client)
        resp = client.post(f'/api/send-email/{meeting_id}', data='{不是json',
                           content_type='application/json')
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_send_email_unknown_meeting_returns_404(self, client):
        resp = client.post('/api/send-email/does-not-exist', json={'recipients': []})
        assert resp.status_code == 404
        assert 'error' in resp.get_json()


# ---------- B. 成本核算口径 ----------

class TestCostCalculator:
    @pytest.mark.parametrize('quantity', [0, -3, 'abc', True, 2.5, None])
    def test_invalid_quantity_returns_400(self, client, quantity):
        resp = client.post('/api/cost-calculator', json={'quantity': quantity})
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_invalid_fabric_type_returns_400(self, client):
        resp = client.post('/api/cost-calculator', json={'fabric_type': 'denim'})
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_invalid_complexity_returns_400(self, client):
        resp = client.post('/api/cost-calculator', json={'complexity': 'nightmare'})
        assert resp.status_code == 400
        assert 'error' in resp.get_json()

    def test_defaults_applied_for_missing_fields(self, client):
        resp = client.post('/api/cost-calculator', json={})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['quantity'] == 1
        assert body['fabric_type'] == 'cotton'
        assert body['complexity'] == 'medium'

    def test_cost_breakdown_matches_spec(self, client):
        resp = client.post('/api/cost-calculator', json={
            'fabric_type': 'silk', 'complexity': 'complex', 'quantity': 3,
        })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['fabric_cost'] == 360.0      # 120 × 3
        assert body['dye_cost'] == 99.0          # 15 × 3 × 2.2
        assert body['labor_cost'] == 528.0       # 80 × 3 × 2.2
        assert body['utility_cost'] == 36.0      # 12 × 3
        assert body['other_cost'] == 24.0        # 8 × 3
        assert body['total_cost'] == 1047.0
        assert body['suggested_retail'] == round(1047.0 * 2.8, 2)

    def test_percentages_sum_to_100(self, client):
        resp = client.post('/api/cost-calculator', json={
            'fabric_type': 'wool', 'complexity': 'medium', 'quantity': 7,
        })
        assert resp.status_code == 200
        body = resp.get_json()
        keys = ['fabric_percentage', 'dye_percentage', 'labor_percentage',
                'utility_percentage', 'other_percentage']
        total_pct = 0.0
        for key in keys:
            assert body[key].endswith('%')
            total_pct += float(body[key].rstrip('%'))
        assert abs(total_pct - 100.0) < 0.5


# ---------- C. 外部服务失败不得伪装成功 ----------

class _FailingCompletions:
    def create(self, **kwargs):
        raise RuntimeError('429 Too Many Requests')


class _FailingClient:
    def __init__(self):
        self.chat = type('Chat', (), {'completions': _FailingCompletions()})()


def _make_offline_summarizer(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    import summarizer
    return summarizer.MeetingSummarizer()


class TestExternalServiceHonesty:
    def test_offline_summary_carries_mock_flag(self, monkeypatch):
        s = _make_offline_summarizer(monkeypatch)
        result = s.generate_summary(
            {'text': '染色2次', 'segments': []},
            {'series_name': '测试系列'},
            {'tie_methods': ['扎结'], 'dye_count_mentions': 1,
             'color_mentions': ['靛蓝']},
        )
        assert result.get('is_mock') is True

    def test_openai_failure_raises_instead_of_template(self, monkeypatch):
        s = _make_offline_summarizer(monkeypatch)
        s.client = _FailingClient()
        with pytest.raises(Exception):
            s.generate_summary({'text': '', 'segments': []}, {}, {})

    def test_process_meeting_openai_failure_returns_error_and_not_persisted(
            self, client, monkeypatch):
        import app as app_module

        def boom(*args, **kwargs):
            raise RuntimeError('429 Too Many Requests')

        monkeypatch.setattr(app_module.summarizer, 'generate_summary', boom)
        resp = post_meeting(client, design_payload())
        assert resp.status_code >= 400
        assert 'error' in resp.get_json()
        # 失败不得落库：模板内容不能作为正式纪要持久化
        assert client.get('/api/meetings').get_json() == []

    def test_transcriber_inference_failure_raises(self):
        from transcriber import MeetingTranscriber
        tr = MeetingTranscriber.__new__(MeetingTranscriber)

        class _BrokenModel:
            def transcribe(self, *args, **kwargs):
                raise RuntimeError('推理失败')

        tr.whisper_model = _BrokenModel()
        with pytest.raises(RuntimeError):
            tr.transcribe_meeting('任意.wav')


# ---------- D. 工艺要素提取 ----------

class TestExtractPatterns:
    @staticmethod
    def _transcriber():
        from transcriber import MeetingTranscriber
        # 绕过 __init__，避免在装有 whisper 的环境里加载模型
        return MeetingTranscriber.__new__(MeetingTranscriber)

    def test_stable_first_appearance_order(self):
        tr = self._transcriber()
        text = '先捆扎再扎结，继续捆扎；染色3次后再染色2次；主色靛蓝，配深蓝与靛蓝'
        patterns = tr.extract_patterns({'text': text})
        assert patterns['tie_methods'] == ['捆扎', '扎结']
        assert patterns['color_mentions'] == ['靛蓝', '深蓝']
        assert patterns['dye_count_mentions'] == 2
        assert patterns['technique_count'] == len(patterns['tie_methods']) + 2

    def test_dye_count_requires_number(self):
        tr = self._transcriber()
        assert tr.extract_patterns({'text': '染色次数要控制好'})['dye_count_mentions'] == 0
        assert tr.extract_patterns({'text': '染色4次再浸染2次'})['dye_count_mentions'] == 2

    def test_repeated_extraction_identical(self):
        tr = self._transcriber()
        text = '夹扎与扎结与夹扎，蓝色和草木染和蓝色，染色5次'
        first = tr.extract_patterns({'text': text})
        second = tr.extract_patterns({'text': text})
        assert first == second

    def test_order_stable_across_processes(self):
        code = (
            "from transcriber import MeetingTranscriber\n"
            "tr = MeetingTranscriber.__new__(MeetingTranscriber)\n"
            "p = tr.extract_patterns({'text': '打绞然后缠绕再扎结然后捆扎，浅蓝配灰蓝再草木染'})\n"
            "print(p['tie_methods'])\n"
            "print(p['color_mentions'])\n"
        )
        outputs = []
        for seed in ('0', '1', '42'):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            out = subprocess.check_output(
                [sys.executable, '-c', code], cwd=BACKEND_DIR, env=env)
            outputs.append(out)
        assert outputs[0] == outputs[1] == outputs[2]


# ---------- E. 会议处理与资源清理 ----------

def _denoised_leftovers():
    return set(glob.glob(os.path.join(tempfile.gettempdir(), '*_denoised*')))


class TestProcessingAndCleanup:
    def test_no_temp_files_left_on_success(self, client):
        before = _denoised_leftovers()
        resp = post_meeting(client, design_payload())
        assert resp.status_code == 200
        assert _denoised_leftovers() == before

    def test_no_temp_files_left_on_failure(self, client, monkeypatch):
        import app as app_module

        def boom(*args, **kwargs):
            raise RuntimeError('外部服务失败')

        monkeypatch.setattr(app_module.summarizer, 'generate_summary', boom)
        before = _denoised_leftovers()
        resp = post_meeting(client, design_payload())
        assert resp.status_code >= 400
        assert _denoised_leftovers() == before

    def test_multiple_audio_files_merged(self, client):
        resp = client.post('/api/process-meeting', data={
            'audio': [
                (io.BytesIO(make_wav_bytes()), '第一段.wav'),
                (io.BytesIO(make_wav_bytes()), '第二段.wav'),
            ],
            'designData': design_payload(),
        }, content_type='multipart/form-data')
        assert resp.status_code == 200
        body = resp.get_json()
        # 两段录音都被转写并合并：既不是只取第一条，也没有重复拼接
        assert len(body['transcript']['segments']) == 8
        assert body['transcript']['text'].count('今天讨论靛蓝系列') == 2

    def test_processed_meeting_has_frontend_fields(self, client):
        meeting_id = create_meeting_id(client)
        detail = client.get(f'/api/meetings/{meeting_id}').get_json()
        assert detail['summary']['series_theme']
        assert detail['summary']['cost_breakdown']['total_cost'] > 0
        assert detail['patterns']['tie_methods']


# ---------- F. 邮件 ----------

class TestEmail:
    def test_unconfigured_service_returns_error_status(self, client):
        meeting_id = create_meeting_id(client)
        resp = client.post(f'/api/send-email/{meeting_id}',
                           json={'recipients': ['buyer@example.com']})
        assert resp.status_code != 200
        assert resp.status_code >= 400
        assert 'error' in resp.get_json()

    def test_empty_recipients_without_default_returns_error(self, client):
        meeting_id = create_meeting_id(client)
        resp = client.post(f'/api/send-email/{meeting_id}', json={'recipients': []})
        assert resp.status_code >= 400
        assert 'error' in resp.get_json()

    def test_delivery_failure_returns_error_status(self, client, monkeypatch):
        import app as app_module

        def boom(*args, **kwargs):
            raise RuntimeError('邮件投递失败：SMTP 连接被拒')

        monkeypatch.setattr(app_module.email_sender, 'send_meeting_summary', boom)
        meeting_id = create_meeting_id(client)
        resp = client.post(f'/api/send-email/{meeting_id}',
                           json={'recipients': ['buyer@example.com']})
        assert resp.status_code >= 400
        assert 'error' in resp.get_json()

    def test_success_only_when_delivered(self, client, monkeypatch):
        import app as app_module
        monkeypatch.setattr(app_module.email_sender, 'send_meeting_summary',
                            lambda *args, **kwargs: True)
        meeting_id = create_meeting_id(client)
        resp = client.post(f'/api/send-email/{meeting_id}',
                           json={'recipients': ['buyer@example.com']})
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

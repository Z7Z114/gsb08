"""行为规格测试：逐条盯住 README「行为规格」的验收点。

这些用例在未修复的实现上应当失败，修复后通过。
"""
import importlib
import io
import json
import os
import struct
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
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('PYANNOTE_AUTH_TOKEN', raising=False)
    monkeypatch.delenv('EMAIL_USER', raising=False)

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


def post_meeting(client, design_data=None, wavs=None):
    if wavs is None:
        wavs = [('会议.wav', make_wav_bytes())]
    files = [(io.BytesIO(content), name) for name, content in wavs]
    return client.post(
        '/api/process-meeting',
        data={'audio': files, 'designData': design_data or design_payload()},
        content_type='multipart/form-data',
    )


def create_meeting(client):
    resp = post_meeting(client)
    assert resp.status_code == 200
    return resp.get_json()['meeting_id']


# ---------- A. 请求校验与错误响应 ----------

def test_process_meeting_invalid_design_data_json(client):
    resp = post_meeting(client, design_data='{not valid json')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_process_meeting_design_data_not_object(client):
    resp = post_meeting(client, design_data='[1, 2, 3]')
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_process_meeting_missing_audio(client):
    resp = client.post(
        '/api/process-meeting',
        data={'designData': design_payload()},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_process_meeting_invalid_quantity_in_design_data(client):
    resp = post_meeting(client, design_data=design_payload(quantity=0))
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_send_email_invalid_json_body(client):
    meeting_id = create_meeting(client)
    resp = client.post(
        f'/api/send-email/{meeting_id}',
        data='not json at all',
        content_type='application/json',
    )
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_send_email_recipients_wrong_type(client):
    meeting_id = create_meeting(client)
    resp = client.post(
        f'/api/send-email/{meeting_id}',
        json={'recipients': 'buyer@example.com'},
    )
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_send_email_unknown_meeting(client):
    resp = client.post('/api/send-email/does-not-exist', json={'recipients': []})
    assert resp.status_code == 404
    assert 'error' in resp.get_json()


def test_cost_calculator_invalid_json_body(client):
    resp = client.post(
        '/api/cost-calculator',
        data='not json at all',
        content_type='application/json',
    )
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


@pytest.mark.parametrize('quantity', [0, -3, 'abc', True, 1.5, None])
def test_cost_calculator_invalid_quantity(client, quantity):
    resp = client.post('/api/cost-calculator', json={'quantity': quantity})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_cost_calculator_invalid_fabric_type(client):
    resp = client.post('/api/cost-calculator', json={'fabric_type': 'polyester'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_cost_calculator_invalid_complexity(client):
    resp = client.post('/api/cost-calculator', json={'complexity': 'hard'})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()


def test_cost_calculator_defaults(client):
    resp = client.post('/api/cost-calculator', json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['quantity'] == 1
    assert body['fabric_type'] == 'cotton'
    assert body['complexity'] == 'medium'
    # cotton=35, medium=1.5: 35 + 15*1.5 + 80*1.5 + 12 + 8 = 197.5
    assert body['total_cost'] == 197.5
    assert body['suggested_retail'] == 553.0


# ---------- B. 成本核算口径 ----------

def test_cost_breakdown_formula_and_percentages(client):
    resp = client.post('/api/cost-calculator', json={
        'fabric_type': 'silk',
        'complexity': 'complex',
        'quantity': 3,
    })
    assert resp.status_code == 200
    body = resp.get_json()
    # silk=120, complex=2.2
    assert body['fabric_cost'] == 360
    assert body['dye_cost'] == 99.0
    assert body['labor_cost'] == 528.0
    assert body['utility_cost'] == 36
    assert body['other_cost'] == 24
    # 分项之和等于总成本
    parts = [body['fabric_cost'], body['dye_cost'], body['labor_cost'],
             body['utility_cost'], body['other_cost']]
    assert body['total_cost'] == 1047.0
    assert abs(sum(parts) - body['total_cost']) < 1e-9
    # 建议零售价 = 总成本 x 2.8
    assert body['suggested_retail'] == round(1047.0 * 2.8, 2)
    # 占比：一位小数、带 %，合计接近 100%
    percentages = []
    for key in ('fabric', 'dye', 'labor', 'utility', 'other'):
        value = body[f'{key}_percentage']
        assert value.endswith('%')
        percentages.append(float(value.rstrip('%')))
    assert abs(sum(percentages) - 100.0) < 0.5


# ---------- C. 外部服务失败不得伪装成功 ----------

def test_offline_summary_carries_mock_flag(client):
    resp = post_meeting(client)
    assert resp.status_code == 200
    assert resp.get_json()['summary'].get('is_mock') is True


def test_summarizer_offline_mock_marked(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    import summarizer
    importlib.reload(summarizer)
    result = summarizer.MeetingSummarizer().generate_summary(
        {'text': '讨论靛蓝', 'segments': []}, {}, {}
    )
    assert result.get('is_mock') is True


def test_summarizer_openai_failure_raises():
    import summarizer

    class FailingCompletions:
        def create(self, **kwargs):
            raise RuntimeError('429 rate limited')

    class FailingChat:
        completions = FailingCompletions()

    class FailingClient:
        chat = FailingChat()

    s = summarizer.MeetingSummarizer()
    s.client = FailingClient()
    with pytest.raises(RuntimeError):
        s.generate_summary({'text': '讨论', 'segments': []}, {}, {})


def test_process_meeting_summary_failure_not_disguised(client, monkeypatch):
    import app as app_module

    def boom(*args, **kwargs):
        raise RuntimeError('OpenAI 429')

    monkeypatch.setattr(app_module.summarizer, 'generate_summary', boom)
    resp = post_meeting(client)
    assert resp.status_code >= 500
    assert 'error' in resp.get_json()
    # 模板内容不得作为正式纪要落库
    assert client.get('/api/meetings').get_json() == []


def test_transcriber_inference_failure_raises():
    import transcriber

    class FailingModel:
        def transcribe(self, *args, **kwargs):
            raise RuntimeError('推理失败')

    t = transcriber.MeetingTranscriber()
    t.whisper_model = FailingModel()
    with pytest.raises(RuntimeError):
        t.transcribe_meeting('whatever.wav')


# ---------- D. 工艺要素提取 ----------

def test_extract_patterns_stable_first_occurrence_order():
    import transcriber

    text = ('先捆扎再扎结，后来又提到捆扎和夹扎；染色4次，再染色2次；'
            '主色靛蓝，配深蓝，最后还是靛蓝。')
    t = transcriber.MeetingTranscriber()
    first = t.extract_patterns({'text': text})
    second = t.extract_patterns({'text': text})

    assert first == second
    assert first['tie_methods'] == ['捆扎', '扎结', '夹扎']
    assert first['color_mentions'] == ['靛蓝', '深蓝']
    assert first['dye_count_mentions'] == 2
    assert first['technique_count'] == len(first['tie_methods']) + first['dye_count_mentions']


# ---------- E. 会议处理与资源清理 ----------

@pytest.fixture()
def temp_dir(tmp_path, monkeypatch):
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    monkeypatch.setattr(tempfile, 'tempdir', str(scratch))
    return scratch


def test_process_meeting_cleans_temp_files(client, temp_dir):
    resp = post_meeting(client)
    assert resp.status_code == 200
    assert list(temp_dir.iterdir()) == []


def test_process_meeting_cleans_temp_files_on_failure(client, monkeypatch, temp_dir):
    import app as app_module

    def boom(*args, **kwargs):
        raise RuntimeError('OpenAI 429')

    monkeypatch.setattr(app_module.summarizer, 'generate_summary', boom)
    resp = post_meeting(client)
    assert resp.status_code >= 500
    assert list(temp_dir.iterdir()) == []


def test_process_meeting_multiple_audios_merged(client):
    resp = post_meeting(client, wavs=[('第一段.wav', make_wav_bytes(1.0)),
                                      ('第二段.wav', make_wav_bytes(1.0))])
    assert resp.status_code == 200
    body = resp.get_json()
    segments = body['transcript']['segments']
    # 两条录音各自转写后合并：不是只取第一条
    assert len(segments) == 8
    # 第二段的时间轴应接在第一段（1 秒）之后
    assert min(s['start'] for s in segments[4:]) >= 1.0
    # 只落库一条会议
    meetings = client.get('/api/meetings').get_json()
    assert len(meetings) == 1
    assert meetings[0]['summary']['series_theme']


# ---------- F. 邮件 ----------

class FakeSMTP:
    deliveries = []
    fail = False

    def __init__(self, host, port):
        self.host = host
        self.port = port

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        pass

    def send_message(self, msg):
        if FakeSMTP.fail:
            raise RuntimeError('SMTP 投递失败')
        FakeSMTP.deliveries.append(msg)


def configure_email(app_module, monkeypatch):
    import email_sender
    monkeypatch.setattr(email_sender.smtplib, 'SMTP', FakeSMTP)
    FakeSMTP.deliveries = []
    FakeSMTP.fail = False
    app_module.email_sender.user = 'workshop@example.com'
    app_module.email_sender.password = 'secret'
    app_module.email_sender.default_recipients = ['buyer@example.com']


def test_send_email_not_configured_returns_error(client):
    meeting_id = create_meeting(client)
    resp = client.post(f'/api/send-email/{meeting_id}', json={'recipients': []})
    assert resp.status_code != 200
    assert 'error' in resp.get_json()


def test_send_email_delivery_failure_returns_error(client, monkeypatch):
    import app as app_module
    configure_email(app_module, monkeypatch)
    FakeSMTP.fail = True

    meeting_id = create_meeting(client)
    resp = client.post(f'/api/send-email/{meeting_id}',
                       json={'recipients': ['buyer@example.com']})
    assert resp.status_code != 200
    assert 'error' in resp.get_json()


def test_send_email_success_and_default_recipients(client, monkeypatch):
    import app as app_module
    configure_email(app_module, monkeypatch)

    meeting_id = create_meeting(client)
    # 收件人为空时回退到默认收件人
    resp = client.post(f'/api/send-email/{meeting_id}', json={'recipients': []})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True
    assert len(FakeSMTP.deliveries) == 1
    assert 'buyer@example.com' in FakeSMTP.deliveries[0]['To']

"""冒烟测试：只覆盖顺利路径。

这些用例在初始快照上应当全绿；它们不覆盖 README「行为规格」里的边界语义，
因此通过它们并不代表规格已被满足。
"""
import importlib
import io
import json
import os
import struct
import sys
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


@pytest.fixture()
def wav_path(tmp_path):
    path = tmp_path / 'meeting.wav'
    path.write_bytes(make_wav_bytes())
    return str(path)


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


def test_health_of_libraries(client):
    resp = client.get('/api/patterns')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 6

    resp = client.get('/api/dyes')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 6


def test_process_meeting_happy_path(client, wav_path):
    with open(wav_path, 'rb') as fh:
        resp = client.post(
            '/api/process-meeting',
            data={'audio': (io.BytesIO(fh.read()), '会议.wav'), 'designData': design_payload()},
            content_type='multipart/form-data',
        )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['meeting_id']
    assert body['summary']['series_theme'] == '靛蓝秋系列'
    assert body['summary']['cost_breakdown']['total_cost'] > 0
    assert 'patterns' in body


def test_meeting_persisted_and_listed(client, wav_path):
    with open(wav_path, 'rb') as fh:
        created = client.post(
            '/api/process-meeting',
            data={'audio': (io.BytesIO(fh.read()), '会议.wav'), 'designData': design_payload()},
            content_type='multipart/form-data',
        ).get_json()

    meeting_id = created['meeting_id']

    listing = client.get('/api/meetings')
    assert listing.status_code == 200
    assert any(m['id'] == meeting_id for m in listing.get_json())

    detail = client.get(f'/api/meetings/{meeting_id}')
    assert detail.status_code == 200
    assert detail.get_json()['audio_file'] == '会议.wav'


def test_meeting_not_found(client):
    resp = client.get('/api/meetings/does-not-exist')
    assert resp.status_code == 404


def test_cost_calculator_valid_input(client):
    resp = client.post('/api/cost-calculator', json={
        'fabric_type': 'cotton',
        'complexity': 'simple',
        'quantity': 1,
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['fabric_cost'] == 35
    assert body['dye_cost'] == 15.0
    assert body['labor_cost'] == 80.0
    assert body['total_cost'] == 150.0
    assert body['suggested_retail'] == 420.0


def test_patterns_endpoint_shape(client):
    patterns = client.get('/api/patterns').get_json()
    first = patterns[0]
    for field in ('id', 'name', 'description', 'technique', 'difficulty', 'tags'):
        assert field in first

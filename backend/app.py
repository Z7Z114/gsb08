import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import tempfile
import json
from datetime import datetime

from audio_processor import AudioProcessor
from transcriber import MeetingTranscriber
from summarizer import MeetingSummarizer
from email_sender import EmailSender
from data_store import DataStore

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

audio_processor = AudioProcessor()
transcriber = MeetingTranscriber()
summarizer = MeetingSummarizer()
email_sender = EmailSender()
data_store = DataStore()


def _parse_json_body():
    """解析 JSON 请求体：无 body 时返回 {}；body 非法（非 JSON 或非对象）时返回 None。"""
    if not request.data:
        return {}
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return None
    return body


def _merge_transcripts(transcripts):
    """合并同一会议多条录音的转写结果：文本按顺序拼接，片段依次衔接，不重复不遗漏。"""
    if len(transcripts) == 1:
        return transcripts[0]
    merged = {
        'language': transcripts[0].get('language', 'zh'),
        'text': '\n'.join(t.get('text', '') for t in transcripts),
        'segments': [seg for t in transcripts for seg in t.get('segments', [])],
    }
    if all(t.get('is_mock') for t in transcripts):
        merged['is_mock'] = True
    return merged


@app.route('/api/process-meeting', methods=['POST'])
def process_meeting():
    audio_files = request.files.getlist('audio')
    if not audio_files:
        return jsonify({'error': 'No audio file provided'}), 400

    try:
        design_data = json.loads(request.form.get('designData', '{}'))
    except (TypeError, ValueError):
        return jsonify({'error': 'designData 不是合法的 JSON'}), 400
    if not isinstance(design_data, dict):
        return jsonify({'error': 'designData 必须是 JSON 对象'}), 400

    try:
        summarizer.validate_cost_params(design_data)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    temp_paths = []
    denoised_paths = []
    try:
        transcripts = []
        speakers = []
        for audio_file in audio_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                audio_file.save(tmp.name)
                temp_paths.append(tmp.name)

            denoised_path = audio_processor.reduce_noise(tmp.name)
            denoised_paths.append(denoised_path)

            transcripts.append(transcriber.transcribe_meeting(denoised_path))
            speakers.extend(transcriber.diarize_speakers(denoised_path))

        transcription = _merge_transcripts(transcripts)

        enriched_transcript = transcriber.enrich_transcript(transcription, speakers)

        patterns = transcriber.extract_patterns(transcription)

        # 外部服务（OpenAI）真实调用失败时此处会抛异常，
        # 由下方 except 转为错误响应，且不会把模板内容写入存储
        summary = summarizer.generate_summary(enriched_transcript, design_data, patterns)

        meeting_id = data_store.save_meeting({
            'timestamp': datetime.now().isoformat(),
            'audio_file': ', '.join(f.filename for f in audio_files),
            'transcript': enriched_transcript,
            'patterns': patterns,
            'summary': summary,
            'design_data': design_data
        })

        return jsonify({
            'meeting_id': meeting_id,
            'transcript': enriched_transcript,
            'patterns': patterns,
            'summary': summary
        })

    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': f'会议处理失败：{exc}'}), 500
    finally:
        # 无论成功或失败，清理本次处理产生的全部临时文件（含降噪分片）
        for path in temp_paths + denoised_paths:
            try:
                if path and os.path.exists(path):
                    os.unlink(path)
            except OSError:
                pass


@app.route('/api/meetings', methods=['GET'])
def get_meetings():
    meetings = data_store.get_all_meetings()
    return jsonify(meetings)


@app.route('/api/meetings/<meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    meeting = data_store.get_meeting(meeting_id)
    if not meeting:
        return jsonify({'error': 'Meeting not found'}), 404
    return jsonify(meeting)


@app.route('/api/send-email/<meeting_id>', methods=['POST'])
def send_email(meeting_id):
    meeting = data_store.get_meeting(meeting_id)
    if not meeting:
        return jsonify({'error': 'Meeting not found'}), 404

    body = _parse_json_body()
    if body is None:
        return jsonify({'error': '请求体必须是合法的 JSON 对象'}), 400

    recipients = body.get('recipients', [])
    if not isinstance(recipients, list) or not all(isinstance(r, str) for r in recipients):
        return jsonify({'error': 'recipients 必须是字符串数组'}), 400

    try:
        email_sender.send_meeting_summary(meeting, recipients)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 502

    return jsonify({'success': True})


@app.route('/api/patterns', methods=['GET'])
def get_patterns():
    patterns = data_store.get_pattern_library()
    return jsonify(patterns)


@app.route('/api/dyes', methods=['GET'])
def get_dyes():
    dyes = data_store.get_dye_library()
    return jsonify(dyes)


@app.route('/api/cost-calculator', methods=['POST'])
def calculate_cost():
    body = _parse_json_body()
    if body is None:
        return jsonify({'error': '请求体必须是合法的 JSON 对象'}), 400

    try:
        cost_breakdown = summarizer.calculate_cost(body)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify(cost_breakdown)


if __name__ == '__main__':
    app.run(debug=True, port=5000)

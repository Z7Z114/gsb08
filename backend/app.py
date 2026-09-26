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


@app.route('/api/process-meeting', methods=['POST'])
def process_meeting():
    audio_files = request.files.getlist('audio')
    if not audio_files:
        return jsonify({'error': 'No audio file provided'}), 400

    try:
        design_data = json.loads(request.form.get('designData', '{}'))
    except (json.JSONDecodeError, TypeError):
        return jsonify({'error': 'designData 不是合法 JSON'}), 400
    if not isinstance(design_data, dict):
        return jsonify({'error': 'designData 必须是 JSON 对象'}), 400

    try:
        summarizer.validate_cost_params(design_data)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    # 本次处理产生的全部临时文件（上传副本 + 降噪分片），无论成败都要清理
    temp_paths = []
    try:
        # 一个会议可能带多条录音：逐条转写/分离后按时间轴合并，再统一提取与摘要
        merged_segments = []
        merged_speakers = []
        merged_texts = []
        all_mock = True
        offset = 0.0

        for audio_file in audio_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                audio_file.save(tmp.name)
                temp_paths.append(tmp.name)

            denoised_path = audio_processor.reduce_noise(tmp.name)
            temp_paths.append(denoised_path)

            transcription = transcriber.transcribe_meeting(denoised_path)
            speakers = transcriber.diarize_speakers(denoised_path)

            for seg in transcription.get('segments', []):
                merged_segments.append({
                    **seg,
                    'start': seg.get('start', 0) + offset,
                    'end': seg.get('end', 0) + offset,
                })
            for spk in speakers:
                merged_speakers.append({
                    **spk,
                    'start': spk.get('start', 0) + offset,
                    'end': spk.get('end', 0) + offset,
                })
            merged_texts.append(transcription.get('text', ''))
            all_mock = all_mock and bool(transcription.get('is_mock'))

            offset += transcriber._get_audio_duration(denoised_path)

        transcription = {
            'language': 'zh',
            'text': ' '.join(t for t in merged_texts if t),
            'segments': merged_segments,
        }
        if all_mock:
            transcription['is_mock'] = True

        enriched_transcript = transcriber.enrich_transcript(transcription, merged_speakers)

        patterns = transcriber.extract_patterns(transcription)

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
        # 外部服务（OpenAI / Whisper 推理等）真实调用失败：如实报错，不落库
        return jsonify({'error': f'会议处理失败：{exc}'}), 502
    finally:
        for path in temp_paths:
            try:
                if os.path.exists(path):
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

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({'error': '请求体必须是合法 JSON 对象'}), 400

    recipients = body.get('recipients', [])
    if not isinstance(recipients, list) or any(not isinstance(r, str) for r in recipients):
        return jsonify({'error': 'recipients 必须是字符串数组'}), 400

    success = email_sender.send_meeting_summary(meeting, recipients)

    if not success:
        # 未配置邮件服务或投递失败：不得用 200 冒充成功
        return jsonify({'error': '邮件未投递：服务未配置或发送失败'}), 502

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
    params = request.get_json(silent=True)
    if not isinstance(params, dict):
        return jsonify({'error': '请求体必须是合法 JSON 对象'}), 400

    try:
        cost_breakdown = summarizer.calculate_cost(params)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify(cost_breakdown)


if __name__ == '__main__':
    app.run(debug=True, port=5000)

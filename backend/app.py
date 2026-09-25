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
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    design_data = json.loads(request.form.get('designData', '{}'))
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
        audio_file.save(tmp.name)
        temp_audio_path = tmp.name
    
    try:
        denoised_path = audio_processor.reduce_noise(temp_audio_path)
        
        transcription = transcriber.transcribe_meeting(denoised_path)
        
        speakers = transcriber.diarize_speakers(denoised_path)
        
        enriched_transcript = transcriber.enrich_transcript(transcription, speakers)
        
        patterns = transcriber.extract_patterns(transcription)
        
        summary = summarizer.generate_summary(enriched_transcript, design_data, patterns)
        
        meeting_id = data_store.save_meeting({
            'timestamp': datetime.now().isoformat(),
            'audio_file': audio_file.filename,
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
        
    finally:
        if os.path.exists(temp_audio_path):
            os.unlink(temp_audio_path)


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
    
    recipients = request.json.get('recipients', [])
    success = email_sender.send_meeting_summary(meeting, recipients)
    
    return jsonify({'success': success})


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
    params = request.json
    cost_breakdown = summarizer.calculate_cost(params)
    return jsonify(cost_breakdown)


if __name__ == '__main__':
    app.run(debug=True, port=5000)

import os
import re

from dotenv import load_dotenv

try:  # 重型语音依赖是可选的：缺失时本模块仍可被导入
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    whisper = None
    WHISPER_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    Pipeline = None
    PYANNOTE_AVAILABLE = False

load_dotenv()


class MeetingTranscriber:
    def __init__(self, model_size="base"):
        self.device = "cuda" if (TORCH_AVAILABLE and torch.cuda.is_available()) else "cpu"
        self.whisper_model = None
        if WHISPER_AVAILABLE:
            self.whisper_model = whisper.load_model(model_size).to(self.device)
        self.diarization_pipeline = None
        
        pyannote_token = os.getenv('PYANNOTE_AUTH_TOKEN')
        if pyannote_token and PYANNOTE_AVAILABLE:
            try:
                self.diarization_pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=pyannote_token
                )
            except Exception as e:
                print(f"Warning: Could not load pyannote pipeline: {e}")
    
    def transcribe_meeting(self, audio_path):
        # 模型未安装/未加载 = 服务不可用：走确定性 mock，便于离线开发与测试。
        if self.whisper_model is None:
            return self._mock_transcription(audio_path)
        
        # 模型已加载则真实推理；若推理失败，异常向上抛出，由调用方决定如何报错。
        result = self.whisper_model.transcribe(
            audio_path,
            language="zh",
            verbose=False,
            word_timestamps=True
        )
        
        segments = []
        for seg in result['segments']:
            segments.append({
                'start': seg['start'],
                'end': seg['end'],
                'text': seg['text'].strip(),
                'words': seg.get('words', [])
            })
        
        return {
            'language': result.get('language', 'zh'),
            'text': result['text'].strip(),
            'segments': segments
        }
    
    def diarize_speakers(self, audio_path):
        if self.diarization_pipeline is None:
            return self._mock_diarization(audio_path)
        
        diarization = self.diarization_pipeline(audio_path)
        
        speakers = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speakers.append({
                'start': turn.start,
                'end': turn.end,
                'speaker': speaker
            })
        
        return speakers
    
    def _mock_transcription(self, audio_path):
        """在未安装 Whisper 时提供的确定性占位转写（供离线开发/测试）。"""
        return {
            'language': 'zh',
            'text': '今天讨论靛蓝系列：主图案用云纹扎结合捆扎，染色4次达到深蓝；'
                    '面料选棉麻，成本控制在合理区间，下周先打样三款。',
            'segments': [
                {'start': 0.0, 'end': 6.0, 'text': '今天讨论靛蓝系列的产品开发'},
                {'start': 6.0, 'end': 14.0, 'text': '主图案用云纹扎结合捆扎手法'},
                {'start': 14.0, 'end': 22.0, 'text': '染色4次可以达到理想深蓝'},
                {'start': 22.0, 'end': 30.0, 'text': '下周先打样三款看效果'},
            ],
            'is_mock': True,
        }

    def _get_audio_duration(self, audio_path):
        # 优先用标准库读取 wav，保证在未安装重型依赖时也能工作
        try:
            import wave
            with wave.open(audio_path, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate() or 1
                return float(frames) / float(rate)
        except Exception:
            pass
        try:
            import librosa
            return float(librosa.get_duration(filename=audio_path))
        except ImportError:
            pass
        try:
            import soundfile as sf
            return float(sf.info(audio_path).duration)
        except Exception as exc:
            raise RuntimeError(
                f"无法读取音频时长（请安装 requirements-ml.txt）：{exc}"
            ) from exc
    
    def _mock_diarization(self, audio_path):
        duration = self._get_audio_duration(audio_path)
        
        segments = []
        current_time = 0
        speaker_idx = 0
        
        while current_time < duration:
            seg_duration = min(30 + (hash(str(current_time)) % 20), duration - current_time)
            segments.append({
                'start': current_time,
                'end': current_time + seg_duration,
                'speaker': f"SPEAKER_{speaker_idx % 2:02d}"
            })
            current_time += seg_duration
            speaker_idx += 1
        
        return segments
    
    def enrich_transcript(self, transcript, speakers):
        enriched_segments = []
        
        for seg in transcript['segments']:
            seg_start = seg['start']
            seg_end = seg['end']
            
            speaker = self._assign_speaker(seg_start, seg_end, speakers)
            
            role = self._identify_role(speaker, seg['text'])
            
            enriched_segments.append({
                **seg,
                'speaker': speaker,
                'role': role
            })
        
        return {
            **transcript,
            'segments': enriched_segments
        }
    
    def _assign_speaker(self, start, end, speakers):
        overlap_max = 0
        assigned_speaker = "UNKNOWN"
        
        for spk in speakers:
            overlap_start = max(start, spk['start'])
            overlap_end = min(end, spk['end'])
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > overlap_max:
                overlap_max = overlap
                assigned_speaker = spk['speaker']
        
        return assigned_speaker
    
    def _identify_role(self, speaker, text):
        designer_keywords = ['设计', '图案', '配色', '系列', '主题', '风格', '元素']
        dyer_keywords = ['染', '靛蓝', '缸', '温度', '时间', '次数', '浓度', '媒染', '固色']
        artisan_keywords = ['扎', '缝', '捆', '绑', '折叠', '手法', '技巧', '工艺']
        
        text_lower = text.lower()
        
        dyer_count = sum(1 for k in dyer_keywords if k in text_lower)
        artisan_count = sum(1 for k in artisan_keywords if k in text_lower)
        designer_count = sum(1 for k in designer_keywords if k in text_lower)
        
        if dyer_count >= 2:
            return '染娘'
        elif artisan_count >= 2:
            return '手工艺人'
        elif designer_count >= 2:
            return '设计师'
        else:
            return '参与者'
    
    def extract_patterns(self, transcript):
        text = transcript['text']
        
        dye_count = len(re.findall(r'(染|染色)(\d+)?次', text))
        tie_methods = re.findall(r'(扎结|捆扎|缝合|折叠|夹扎|缠绕|打绞)', text)
        
        color_counts = re.findall(r'(靛蓝|蓝色|青色|深蓝|浅蓝|灰蓝|植物染|草木染)', text)
        
        patterns = {
            'tie_methods': list(set(tie_methods)),
            'dye_count_mentions': dye_count,
            'color_mentions': list(set(color_counts)),
            'technique_count': len(tie_methods) + dye_count
        }
        
        return patterns

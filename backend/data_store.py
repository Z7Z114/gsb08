import json
import os
import uuid
from datetime import datetime


class DataStore:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = os.getenv('DATA_DIR', 'data')
        self.data_dir = data_dir
        self.meetings_file = os.path.join(data_dir, 'meetings.json')
        self.patterns_file = os.path.join(data_dir, 'patterns.json')
        self.dyes_file = os.path.join(data_dir, 'dyes.json')
        
        os.makedirs(data_dir, exist_ok=True)
        self._init_files()
    
    def _init_files(self):
        if not os.path.exists(self.meetings_file):
            with open(self.meetings_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.patterns_file):
            default_patterns = [
                {
                    'id': 'p1',
                    'name': '云纹扎',
                    'description': '传统云纹图案，采用捆扎技法形成自然流云效果',
                    'technique': '捆扎法',
                    'difficulty': '中等',
                    'dye_count': 3,
                    'image_url': '/patterns/cloud.jpg',
                    'tags': ['传统', '抽象', '自然']
                },
                {
                    'id': 'p2',
                    'name': '水波纹',
                    'description': '模拟水波涟漪的动态效果，线条流畅自然',
                    'technique': '折叠扎',
                    'difficulty': '简单',
                    'dye_count': 2,
                    'image_url': '/patterns/wave.jpg',
                    'tags': ['自然', '动态', '简约']
                },
                {
                    'id': 'p3',
                    'name': '几何菱格',
                    'description': '现代几何设计，菱格交错形成秩序美感',
                    'technique': '夹扎法',
                    'difficulty': '中等',
                    'dye_count': 2,
                    'image_url': '/patterns/geometric.jpg',
                    'tags': ['现代', '几何', '简约']
                },
                {
                    'id': 'p4',
                    'name': '冰裂纹',
                    'description': '仿冰面裂纹效果，纹理细碎而富有变化',
                    'technique': '揉皱法',
                    'difficulty': '复杂',
                    'dye_count': 4,
                    'image_url': '/patterns/ice.jpg',
                    'tags': ['抽象', '自然', '复杂']
                },
                {
                    'id': 'p5',
                    'name': '螺旋纹',
                    'description': '从中心向外旋转的螺旋图案，富有动感',
                    'technique': '螺旋扎',
                    'difficulty': '简单',
                    'dye_count': 2,
                    'image_url': '/patterns/spiral.jpg',
                    'tags': ['动态', '经典', '简约']
                },
                {
                    'id': 'p6',
                    'name': '花瓣纹',
                    'description': '模拟花瓣层叠的柔美效果，适合女性化产品',
                    'technique': '放射扎',
                    'difficulty': '复杂',
                    'dye_count': 3,
                    'image_url': '/patterns/petal.jpg',
                    'tags': ['自然', '柔美', '花卉']
                }
            ]
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(default_patterns, f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(self.dyes_file):
            default_dyes = [
                {
                    'id': 'd1',
                    'name': '板蓝根靛蓝',
                    'color': '#1e3a5f',
                    'source': '板蓝根植物发酵',
                    'origin': '云南大理',
                    'properties': ['天然', '环保', '抗菌'],
                    'ph_range': '9-10',
                    'temperature': '50-60°C',
                    'price_per_kg': 180
                },
                {
                    'id': 'd2',
                    'name': '蓼蓝',
                    'color': '#2d5a87',
                    'source': '蓼蓝草发酵',
                    'origin': '贵州苗寨',
                    'properties': ['传统', '耐用', '色泽饱满'],
                    'ph_range': '8.5-9.5',
                    'temperature': '45-55°C',
                    'price_per_kg': 220
                },
                {
                    'id': 'd3',
                    'name': '木蓝',
                    'color': '#3d6e99',
                    'source': '木蓝茎叶提取',
                    'origin': '广西壮族',
                    'properties': ['清新', '淡雅', '易上色'],
                    'ph_range': '9-10',
                    'temperature': '50-65°C',
                    'price_per_kg': 160
                },
                {
                    'id': 'd4',
                    'name': '槐蓝',
                    'color': '#1a2f4a',
                    'source': '槐树豆荚提取',
                    'origin': '河南',
                    'properties': ['深色', '浓郁', '古典'],
                    'ph_range': '8.5-10',
                    'temperature': '55-65°C',
                    'price_per_kg': 250
                },
                {
                    'id': 'd5',
                    'name': '马蓝',
                    'color': '#2a4a6e',
                    'source': '马蓝草发酵',
                    'origin': '湖南湘西',
                    'properties': ['中性', '稳定', '适合初学者'],
                    'ph_range': '8-9.5',
                    'temperature': '45-60°C',
                    'price_per_kg': 190
                },
                {
                    'id': 'd6',
                    'name': '青黛',
                    'color': '#4a7a9e',
                    'source': '靛蓝提纯粉末',
                    'origin': '江苏',
                    'properties': ['高纯度', '医药级', '细腻'],
                    'ph_range': '7.5-9',
                    'temperature': '40-50°C',
                    'price_per_kg': 380
                }
            ]
            with open(self.dyes_file, 'w', encoding='utf-8') as f:
                json.dump(default_dyes, f, ensure_ascii=False, indent=2)
    
    def save_meeting(self, meeting_data):
        meetings = self._read_json(self.meetings_file)
        
        meeting_id = str(uuid.uuid4())
        meeting_data['id'] = meeting_id
        
        meetings.insert(0, meeting_data)
        
        self._write_json(self.meetings_file, meetings)
        
        return meeting_id
    
    def get_all_meetings(self):
        meetings = self._read_json(self.meetings_file)
        return meetings
    
    def get_meeting(self, meeting_id):
        meetings = self._read_json(self.meetings_file)
        for m in meetings:
            if m.get('id') == meeting_id:
                return m
        return None
    
    def get_pattern_library(self):
        return self._read_json(self.patterns_file)
    
    def get_dye_library(self):
        return self._read_json(self.dyes_file)
    
    def _read_json(self, filepath):
        if not os.path.exists(filepath):
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write_json(self, filepath, data):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

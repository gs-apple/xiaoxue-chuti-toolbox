# zuowen_data.py - 作文数据层
# 数据从 JSON 文件加载

import json
import os

_DATA_DIR = os.path.dirname(os.path.abspath(__file__))

def _load_json(filename):
    filepath = os.path.join(_DATA_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

# 加载所有数据
_data = _load_json('zuowen_data.json')

TEXTBOOK_COMPS = _data.get('TEXTBOOK_COMPS', {})
EXAMPLE_ESSAYS = _data.get('EXAMPLE_ESSAYS', {})
PICTURE_WRITING = _data.get('PICTURE_WRITING', [])
ZHONGKAO = _data.get('ZHONGKAO', {})
GAOKAO = _data.get('GAOKAO', {})

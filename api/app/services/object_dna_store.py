
from __future__ import annotations
import os, json, time, uuid
from typing import Dict, Any, List, Optional
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'object_dna_store.json'))
def _load() -> Dict[str, list]:
    if not os.path.exists(DATA_PATH):
        data = {'records': []}
        with open(DATA_PATH, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
        return data
    with open(DATA_PATH, 'r', encoding='utf-8') as f: return json.load(f)
def _save(data: Dict[str, list]) -> None:
    with open(DATA_PATH, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
def _id(prefix: str = 'dna') -> str: return f"{prefix}_{uuid.uuid4().hex[:10]}"
def create_record(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = _load()
    record = {'id': _id(), 'title': payload.get('title') or 'Untitled Object', 'source_flow': payload.get('source_flow') or 'manual', 'created_at': int(time.time()), 'updated_at': int(time.time()), 'object_dna': payload.get('object_dna') or {'geometry': {}, 'structure': {}, 'print_profile': {}, 'ai_generation': {}, 'user_edits': [], 'outcomes': {}}, 'links': payload.get('links') or {}, 'tags': payload.get('tags') or []}
    data['records'].insert(0, record); _save(data); return record

def list_records(limit: int = 100) -> List[Dict[str, Any]]: return _load().get('records', [])[:limit]
def get_record(record_id: str) -> Optional[Dict[str, Any]]: return next((r for r in _load().get('records', []) if r.get('id') == record_id), None)
def update_record(record_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    data = _load()
    for record in data.get('records', []):
        if record.get('id') == record_id:
            if 'title' in payload: record['title'] = payload['title']
            if 'tags' in payload: record['tags'] = payload['tags']
            if 'links' in payload: record['links'] = payload['links']
            if 'object_dna' in payload:
                incoming = payload['object_dna'] or {}
                current = record.get('object_dna') or {}
                for key, value in incoming.items(): current[key] = value
                record['object_dna'] = current
            if 'append_user_edit' in payload: record.setdefault('object_dna', {}).setdefault('user_edits', []).append(payload['append_user_edit'])
            if 'merge_outcomes' in payload: record.setdefault('object_dna', {}).setdefault('outcomes', {}).update(payload['merge_outcomes'] or {})
            record['updated_at'] = int(time.time()); _save(data); return record
    return None


from __future__ import annotations
from typing import Dict, Any
from app.services.object_dna_store import create_record, update_record

def _base_dna() -> Dict[str, Any]:
    return {'geometry': {}, 'structure': {}, 'print_profile': {}, 'ai_generation': {}, 'user_edits': [], 'outcomes': {}}

def write_from_scan(payload: Dict[str, Any]) -> Dict[str, Any]:
    object_dna = _base_dna(); object_dna['geometry'] = {'family': payload.get('family') or payload.get('label') or 'object', 'dimensions_mm': payload.get('dimensions_mm') or {}}; object_dna['ai_generation'] = {'source': 'scan_accept', 'confidence': payload.get('confidence'), 'workflow': payload.get('workflow') or 'scan_world'}
    return create_record({'title': payload.get('title') or f"Scanned {object_dna['geometry']['family']}", 'source_flow': 'scan', 'object_dna': object_dna, 'tags': payload.get('tags') or ['scan']})

def write_from_fix(payload: Dict[str, Any]) -> Dict[str, Any]:
    fix_plan = payload.get('fix_plan') or {}
    object_dna = fix_plan.get('object_dna') or _base_dna(); object_dna.setdefault('ai_generation', {})['bridge_source'] = 'fix_object'
    return create_record({'title': payload.get('title') or f"Repair {fix_plan.get('replacement_family') or payload.get('label') or 'object'}", 'source_flow': 'fix', 'object_dna': object_dna, 'tags': payload.get('tags') or ['repair']})

def write_from_ar(payload: Dict[str, Any]) -> Dict[str, Any]:
    ar_plan = payload.get('ar_plan') or {}
    object_dna = ar_plan.get('object_dna') or _base_dna(); object_dna.setdefault('outcomes', {})['ar_fit_previewed'] = True
    return create_record({'title': payload.get('title') or ar_plan.get('design_title') or 'AR Preview', 'source_flow': 'ar', 'object_dna': object_dna, 'tags': payload.get('tags') or ['ar']})

def write_print_outcome(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    record_id = payload.get('record_id')
    if not record_id: return None
    merged = {'printed': bool(payload.get('printed', True)), 'print_success': bool(payload.get('print_success', False)), 'printer_id': payload.get('printer_id'), 'material': payload.get('material'), 'rating': payload.get('rating'), 'notes': payload.get('notes')}
    return update_record(record_id, {'merge_outcomes': merged})

def append_user_edit(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    record_id = payload.get('record_id')
    if not record_id: return None
    edit = {'type': payload.get('type') or 'manual_edit', 'before': payload.get('before'), 'after': payload.get('after'), 'reason': payload.get('reason')}
    return update_record(record_id, {'append_user_edit': edit})

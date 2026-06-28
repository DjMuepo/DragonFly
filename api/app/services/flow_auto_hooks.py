from app.services.object_dna_flow_bridge import write_from_scan, write_from_fix, write_from_ar, write_print_outcome, append_user_edit

def auto_hook_scan_accept(payload): return write_from_scan(payload)
def auto_hook_fix_accept(payload): return write_from_fix(payload)
def auto_hook_ar_confirm(payload): return write_from_ar(payload)
def auto_hook_print_complete(payload): return write_print_outcome(payload)
def auto_hook_user_edit(payload): return append_user_edit(payload)

from app.services.object_dna_store import list_records

def summarize_learning(limit: int = 500):
    records = list_records(limit=limit)
    families = {}
    total = len(records)
    for r in records:
        dna = r.get("object_dna") or {}
        family = (dna.get("geometry") or {}).get("family") or "unknown"
        outcomes = dna.get("outcomes") or {}
        edits = dna.get("user_edits") or []
        fam = families.setdefault(family, {
            "count": 0, "printed": 0, "success": 0,
            "edit_count": 0, "materials": {}, "top_edit_types": {}
        })
        fam["count"] += 1
        if outcomes.get("printed"): fam["printed"] += 1
        if outcomes.get("print_success"): fam["success"] += 1
        fam["edit_count"] += len(edits)
        material = (dna.get("print_profile") or {}).get("material")
        if material:
            fam["materials"][material] = fam["materials"].get(material, 0) + 1
        for e in edits:
            et = e.get("type") or "manual_edit"
            fam["top_edit_types"][et] = fam["top_edit_types"].get(et, 0) + 1

    recommendations = []
    for family, stats in families.items():
        print_rate = stats["printed"] / max(1, stats["count"])
        success_rate = stats["success"] / max(1, stats["printed"] or 1)
        top_material = sorted(stats["materials"].items(), key=lambda x: x[1], reverse=True)[0][0] if stats["materials"] else None
        top_edit = sorted(stats["top_edit_types"].items(), key=lambda x: x[1], reverse=True)[0][0] if stats["top_edit_types"] else None
        recommendations.append({
            "family": family,
            "records": stats["count"],
            "print_rate": round(print_rate, 3),
            "success_rate": round(success_rate, 3),
            "recommended_material": top_material,
            "suggested_default_edit": top_edit,
            "message": f"For {family}, strongest signal suggests material={top_material or 'unknown'} and default edit={top_edit or 'none'}."
        })
    recommendations.sort(key=lambda x: (x["success_rate"], x["records"]), reverse=True)
    return {"ok": True, "total_records": total, "families": families, "recommendations": recommendations[:20]}

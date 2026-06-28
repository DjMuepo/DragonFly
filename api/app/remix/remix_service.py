
from __future__ import annotations
import copy
from typing import Dict, Any

def remix_design(original: Dict[str, Any], new_creator: str) -> Dict[str, Any]:
    new = copy.deepcopy(original)
    new["remix_of"] = original.get("slug")
    new["creator"] = new_creator
    new["likes"] = 0
    new["title"] = f"Remix of {original.get('title','design')}"
    return new

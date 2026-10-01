from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import trimesh


class UnsupportedEditError(ValueError):
    pass


@dataclass(frozen=True)
class EditResult:
    mesh: trimesh.Trimesh
    change_kind: str
    summary: str
    operations: list[str]


class FeatureEditingProvider:
    name = "deterministic-feature-editor"
    supported_features = ("base",)

    def apply(self, mesh: trimesh.Trimesh, prompt: str) -> EditResult | None:
        lowered = prompt.lower()
        feature_request = re.search(r"\b(add|remove|delete|cut|create)\b", lowered)
        if not feature_request:
            return None
        if "base" not in lowered:
            raise UnsupportedEditError(
                "This editor currently supports adding or removing a base. Holes, handles, and freeform parts require a configured generative editing provider."
            )
        if re.search(r"\b(remove|delete)\b", lowered):
            parts = list(mesh.split(only_watertight=False))
            if len(parts) < 2:
                raise UnsupportedEditError("No separate base feature was found to remove. Use Undo if the base was added in this session.")
            lowest = min(range(len(parts)), key=lambda index: float(parts[index].centroid[2]))
            remaining = [part for index, part in enumerate(parts) if index != lowest]
            return EditResult(trimesh.util.concatenate(remaining), "geometry", "Removed the lowest separate base feature.", ["remove base"])

        thickness_match = re.search(r"(?:base\s+)?(\d+(?:\.\d+)?)\s*mm\s*(?:thick|thickness)?", lowered)
        thickness = float(thickness_match.group(1)) if thickness_match else max(2.0, float(mesh.extents[2]) * 0.08)
        base = trimesh.creation.box(extents=(float(mesh.extents[0]) * 1.1, float(mesh.extents[1]) * 1.1, thickness))
        base.apply_translation((float(mesh.centroid[0]), float(mesh.centroid[1]), float(mesh.bounds[0][2]) - thickness / 2))
        return EditResult(trimesh.util.concatenate((mesh, base)), "geometry", f"Added a {thickness:g} mm base.", ["add base"])


class DeterministicMeshEditor:
    def __init__(self) -> None:
        self.features = FeatureEditingProvider()

    def apply(self, mesh: trimesh.Trimesh, prompt: str) -> EditResult:
        text = prompt.strip()
        if not text:
            raise UnsupportedEditError("Enter an editing instruction.")
        feature_result = self.features.apply(mesh, text)
        if feature_result:
            return feature_result

        result = mesh.copy()
        lowered = text.lower()
        operations: list[str] = []
        scale = np.ones(3)

        percent = self._number(r"(\d+(?:\.\d+)?)\s*%\s*(?:larger|bigger)", lowered)
        if percent is not None:
            scale *= 1 + percent / 100
            operations.append(f"scale {percent:g}% larger")
        percent = self._number(r"(\d+(?:\.\d+)?)\s*%\s*(?:smaller)", lowered)
        if percent is not None:
            scale *= max(0.01, 1 - percent / 100)
            operations.append(f"scale {percent:g}% smaller")
        for axis, words in enumerate((("wide", "width"), ("deep", "depth"), ("tall", "high", "height"))):
            target = self._number(rf"(\d+(?:\.\d+)?)\s*mm\s*(?:{'|'.join(words)})", lowered)
            if target is not None:
                scale[axis] *= target / max(float(result.extents[axis]), 1e-6)
                operations.append(f"set {words[-1]} to {target:g} mm")
            wider = self._number(rf"(\d+(?:\.\d+)?)\s*%\s*(?:{'|'.join(words)})(?:er)?", lowered)
            if wider is not None:
                scale[axis] *= 1 + wider / 100
                operations.append(f"increase {words[-1]} {wider:g}%")
        if not np.allclose(scale, 1):
            transform = np.eye(4)
            transform[:3, :3] = np.diag(scale)
            result.apply_transform(transform)

        rotation = self._number(r"rotate\s+(-?\d+(?:\.\d+)?)\s*(?:degrees?|deg)?", lowered)
        if rotation is not None:
            axis_name = next((axis for axis in "xyz" if re.search(rf"(?:around|on)\s+(?:the\s+)?{axis}(?:\s*axis)?", lowered)), "z")
            axis = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis_name]
            result.apply_transform(trimesh.transformations.rotation_matrix(np.radians(rotation), axis, point=result.centroid))
            operations.append(f"rotate {rotation:g} degrees around {axis_name}")

        translation = np.zeros(3)
        directions = {"right": (0, 1), "left": (0, -1), "back": (1, 1), "forward": (1, -1), "up": (2, 1), "down": (2, -1)}
        for word, (axis, sign) in directions.items():
            distance = self._number(rf"(?:move|position|shift)\s+(\d+(?:\.\d+)?)\s*mm\s+{word}", lowered)
            if distance is not None:
                translation[axis] += sign * distance
                operations.append(f"move {distance:g} mm {word}")
        if not np.allclose(translation, 0):
            result.apply_translation(translation)

        color = next((name for name in ("red", "blue", "green", "black", "white", "gray", "yellow") if re.search(rf"\b{name}\b", lowered)), None)
        if color and re.search(r"\b(color|colour|material|paint|make)\b", lowered):
            rgba = {"red": [220, 45, 45, 255], "blue": [45, 105, 220, 255], "green": [45, 170, 90, 255], "black": [25, 25, 25, 255], "white": [240, 240, 240, 255], "gray": [130, 130, 130, 255], "yellow": [235, 190, 35, 255]}[color]
            result.visual.face_colors = rgba
            return EditResult(result, "visual_only", f"Changed the preview material to {color}; STL geometry is unchanged.", [f"material {color}"])

        if not operations:
            raise UnsupportedEditError(
                "Unsupported instruction. Try scaling, exact dimensions, rotation, positioning, color, or adding/removing a base."
            )
        return EditResult(result, "geometry", "; ".join(operations).capitalize() + ".", operations)

    @staticmethod
    def _number(pattern: str, text: str) -> float | None:
        match = re.search(pattern, text)
        return float(match.group(1)) if match else None


def validate_for_print(mesh: trimesh.Trimesh) -> dict:
    extents = [round(float(value), 2) for value in mesh.extents]
    warnings: list[str] = []
    if not mesh.is_watertight:
        warnings.append("Mesh is not watertight and may need repair before printing.")
    if min(extents) < 1:
        warnings.append("One dimension is under 1 mm and may be too thin to print.")
    if len(list(mesh.split(only_watertight=False))) > 1:
        warnings.append("Mesh contains multiple disconnected parts.")
    return {"watertight": bool(mesh.is_watertight), "dimensions_mm": {"width": extents[0], "depth": extents[1], "height": extents[2]}, "warnings": warnings}
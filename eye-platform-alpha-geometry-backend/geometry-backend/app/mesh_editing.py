from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
import trimesh


class UnsupportedEditError(ValueError):
    pass


class ClarificationRequiredError(UnsupportedEditError):
    pass


@dataclass(frozen=True)
class StructuredOperation:
    kind: str
    axis: int | None = None
    value: float | str | None = None
    description: str = ""


@dataclass(frozen=True)
class EditIntent:
    operations: list[StructuredOperation]
    source: str = "structured-language-interpreter"


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


class EditIntentInterpreter:
    axis_names = {"width": 0, "wide": 0, "depth": 1, "deep": 1, "height": 2, "high": 2, "tall": 2}

    def interpret(self, mesh: trimesh.Trimesh, prompt: str) -> EditIntent:
        text = re.sub(r"[^a-z0-9.%+-]+", " ", prompt.lower()).strip()
        operations: list[StructuredOperation] = []

        for match in re.finditer(r"(\d+(?:\.\d+)?)\s*%\s*(larger|bigger|smaller)", text):
            percent, direction = float(match.group(1)), match.group(2)
            factor = 1 + percent / 100 if direction != "smaller" else max(0.01, 1 - percent / 100)
            operations.append(StructuredOperation("scale_uniform", value=factor, description=f"scale {percent:g}% {direction}"))

        dimension_words = "width|wide|depth|deep|height|high|tall"
        for match in re.finditer(rf"(\d+(?:\.\d+)?)\s*mm\s*({dimension_words})", text):
            target, word = float(match.group(1)), match.group(2)
            axis = self.axis_names[word]
            operations.append(StructuredOperation("set_dimension", axis, target, f"set {self._axis_label(axis)} to {target:g} mm"))

        for match in re.finditer(rf"increase\s+(?:the\s+|its\s+)?({dimension_words})\s+by\s+(\d+(?:\.\d+)?)\s*(%|mm)", text):
            word, amount, unit = match.group(1), float(match.group(2)), match.group(3)
            axis = self.axis_names[word]
            kind = "scale_axis" if unit == "%" else "increase_dimension"
            value = 1 + amount / 100 if unit == "%" else amount
            operations.append(StructuredOperation(kind, axis, value, f"increase {self._axis_label(axis)} by {amount:g}{unit}"))

        for match in re.finditer(rf"(\d+(?:\.\d+)?)\s*%\s*({dimension_words})(?:er)?", text):
            amount, word = float(match.group(1)), match.group(2)
            axis = self.axis_names[word]
            operations.append(StructuredOperation("scale_axis", axis, 1 + amount / 100, f"increase {self._axis_label(axis)} by {amount:g}%"))

        rotation = re.search(r"rotate(?:\s+(?:the\s+)?(?:bottle|object|model|item|it|this\s+\w+))?\s+(-?\d+(?:\.\d+)?)\s*(?:degrees?|deg)?", text)
        if rotation:
            axis_match = re.search(r"(?:around|on)\s+(?:the\s+)?([xyz])(?:\s*axis)?", text)
            axis = {"x": 0, "y": 1, "z": 2}.get(axis_match.group(1) if axis_match else "z", 2)
            angle = float(rotation.group(1))
            operations.append(StructuredOperation("rotate", axis, angle, f"rotate {angle:g} degrees around {'xyz'[axis]}"))

        directions = {"right": (0, 1), "left": (0, -1), "back": (1, 1), "forward": (1, -1), "up": (2, 1), "down": (2, -1)}
        for word, (axis, sign) in directions.items():
            match = re.search(rf"(?:move|position|shift)(?:\s+(?:the\s+)?(?:bottle|object|model|item|it))?\s+(\d+(?:\.\d+)?)\s*mm\s+{word}", text)
            if match:
                amount = float(match.group(1))
                operations.append(StructuredOperation("translate", axis, sign * amount, f"move {amount:g} mm {word}"))

        color = next((name for name in ("red", "blue", "green", "black", "white", "gray", "yellow") if re.search(rf"\b{name}\b", text)), None)
        if color and re.search(r"\b(color|colour|material|paint|make|change)\b", text):
            operations.append(StructuredOperation("material", value=color, description=f"material {color}"))

        vague = next((word for word in ("taller", "wider", "deeper", "larger", "bigger", "smaller") if re.search(rf"\b{word}\b", text)), None)
        if vague and not operations:
            dimension = {"taller": "height", "wider": "width", "deeper": "depth"}.get(vague, "overall size")
            raise ClarificationRequiredError(f"How much should I change the {dimension}? Enter a percentage or an exact dimension in mm.")
        if not operations:
            raise UnsupportedEditError(
                "Unsupported instruction. Try a percentage or exact dimension, rotation, position, color, or add/remove base."
            )
        return EditIntent(operations)

    @staticmethod
    def _axis_label(axis: int) -> str:
        return ("width", "depth", "height")[axis]


class DeterministicMeshEditor:
    def __init__(self) -> None:
        self.features = FeatureEditingProvider()
        self.interpreter = EditIntentInterpreter()

    def apply(self, mesh: trimesh.Trimesh, prompt: str) -> EditResult:
        text = prompt.strip()
        if not text:
            raise UnsupportedEditError("Enter an editing instruction.")
        feature_result = self.features.apply(mesh, text)
        if feature_result:
            return feature_result

        result = mesh.copy()
        intent = self.interpreter.interpret(result, text)
        descriptions: list[str] = []
        visual_only = True
        colors = {"red": [220, 45, 45, 255], "blue": [45, 105, 220, 255], "green": [45, 170, 90, 255], "black": [25, 25, 25, 255], "white": [240, 240, 240, 255], "gray": [130, 130, 130, 255], "yellow": [235, 190, 35, 255]}
        for operation in intent.operations:
            descriptions.append(operation.description)
            if operation.kind == "material":
                result.visual.vertex_colors = np.tile(colors[str(operation.value)], (len(result.vertices), 1))
                continue
            visual_only = False
            if operation.kind == "scale_uniform":
                result.apply_scale(float(operation.value))
            elif operation.kind in {"scale_axis", "set_dimension", "increase_dimension"}:
                factors = np.ones(3)
                if operation.kind == "scale_axis":
                    factors[operation.axis] = float(operation.value)
                elif operation.kind == "set_dimension":
                    factors[operation.axis] = float(operation.value) / max(float(result.extents[operation.axis]), 1e-6)
                else:
                    factors[operation.axis] = (float(result.extents[operation.axis]) + float(operation.value)) / max(float(result.extents[operation.axis]), 1e-6)
                transform = np.eye(4)
                transform[:3, :3] = np.diag(factors)
                result.apply_transform(transform)
            elif operation.kind == "rotate":
                axis = np.eye(3)[operation.axis]
                result.apply_transform(trimesh.transformations.rotation_matrix(np.radians(float(operation.value)), axis, point=result.centroid))
            elif operation.kind == "translate":
                translation = np.zeros(3)
                translation[operation.axis] = float(operation.value)
                result.apply_translation(translation)
        if visual_only:
            color = next(str(operation.value) for operation in intent.operations if operation.kind == "material")
            return EditResult(result, "visual_only", f"Changed the preview material to {color}; STL geometry is unchanged.", descriptions)
        return EditResult(result, "geometry", "; ".join(descriptions).capitalize() + ".", descriptions)


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
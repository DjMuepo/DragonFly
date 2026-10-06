from __future__ import annotations

import re
from dataclasses import dataclass, field

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
    feature_metadata: dict = field(default_factory=dict)


class FeatureEditingProvider:
    name = "deterministic-feature-editor"
    supported_features = ("through_hole", "hollow_box", "cut_box", "base_box", "handle_loop")

    @staticmethod
    def _boolean(mesh: trimesh.Trimesh, tool: trimesh.Trimesh, operation: str) -> trimesh.Trimesh:
        try:
            result = getattr(trimesh.boolean, operation)([mesh, tool], engine="manifold")
        except (ImportError, ValueError, RuntimeError) as error:
            raise UnsupportedEditError(f"Boolean mesh operation failed validation: {error}") from None
        if result is None or result.is_empty or len(result.faces) == 0 or not result.is_watertight:
            raise UnsupportedEditError("The requested feature did not produce a valid watertight mesh.")
        return result

    @staticmethod
    def _box_mesh(mesh: trimesh.Trimesh) -> bool:
        return len(mesh.vertices) <= 32 and len(mesh.faces) <= 48 and mesh.is_watertight

    @staticmethod
    def _hollow_mesh(mesh: trimesh.Trimesh, thickness: float) -> trimesh.Trimesh:
        import manifold3d

        if thickness <= 0:
            raise UnsupportedEditError("Wall thickness must be greater than zero mm.")
        source = manifold3d.Manifold(
            manifold3d.Mesh(
                np.asarray(mesh.vertices, dtype=np.float32),
                np.asarray(mesh.faces, dtype=np.uint32),
            )
        )
        if source.status() != manifold3d.Error.NoError or source.is_empty():
            raise UnsupportedEditError("The source mesh could not be converted to a valid manifold for hollowing.")
        inner = source.minkowski_difference(manifold3d.Manifold.sphere(thickness, 8))
        if inner.status() != manifold3d.Error.NoError or inner.is_empty() or inner.volume() <= 0:
            raise UnsupportedEditError("That wall thickness leaves no valid interior cavity in this mesh.")
        shell = source - inner
        if shell.status() != manifold3d.Error.NoError or shell.is_empty() or shell.volume() <= 0:
            raise UnsupportedEditError("Hollowing did not produce a valid positive-volume shell.")
        shell_mesh = shell.to_mesh()
        result = trimesh.Trimesh(
            vertices=np.asarray(shell_mesh.vert_properties[:, :3]),
            faces=np.asarray(shell_mesh.tri_verts),
            process=True,
        )
        if result.is_empty or not result.is_watertight:
            raise UnsupportedEditError("Hollowing did not produce a watertight shell.")
        return result

    def apply(self, mesh: trimesh.Trimesh, prompt: str, scale_status: str = "unknown", feature_metadata: dict | None = None) -> EditResult | None:
        lowered = prompt.lower()
        feature_request = re.search(r"\b(add|remove|delete|cut|create)\b", lowered)
        advanced = re.search(r"\b(hole|through[- ]hole|hollow|wall thickness|walls|cut|trim|handle|fillet|round|chamfer|thread)\b", lowered)
        if re.search(r"\b(fillet|round(?:ed|ing)?|chamfer|thread(?:s|ed)?)\b", lowered):
            raise UnsupportedEditError("Fillet, chamfer, and threads are not implemented as real mesh operations yet.")
        if not feature_request and not advanced:
            return None
        if scale_status != "calibrated":
            raise ClarificationRequiredError("Calibrate the model before adding or removing physical-size features.")
        if not mesh.is_watertight:
            raise UnsupportedEditError("This feature requires a watertight source mesh. Repair or regenerate the model first.")

        hole = re.search(r"(?:hole|through[- ]hole)\D{0,32}(\d+(?:\.\d+)?)\s*mm|put\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*mm\s+hole|(\d+(?:\.\d+)?)\s*mm\s*(?:diameter|hole|through[- ]hole)", lowered)
        if "hole" in lowered or "through-hole" in lowered or "through hole" in lowered:
            match = hole
            if not match:
                raise ClarificationRequiredError("What diameter should the hole be? Give a measurement in mm.")
            diameter = float(match.group(1) or match.group(2) or match.group(3))
            axis = next((name for name in "xyz" if re.search(rf"through\s+(?:the\s+)?{name}(?:\s+axis)?", lowered)), "z")
            axis_index = {"x": 0, "y": 1, "z": 2}[axis]
            tool = trimesh.creation.cylinder(radius=diameter / 2, height=float(np.linalg.norm(mesh.extents)) * 2, sections=64)
            if axis_index == 0:
                tool.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0)))
            elif axis_index == 1:
                tool.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (1, 0, 0)))
            tool.apply_translation(mesh.bounding_box.centroid)
            result = self._boolean(mesh, tool, "difference")
            return EditResult(result, "geometry", f"Cut a {diameter:g} mm through-hole along {axis}.", [f"through-hole {diameter:g} mm {axis}"])

        if "hollow" in lowered or "wall thickness" in lowered or "walls" in lowered:
            thickness_match = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*(?:wall|walls|thick)", lowered)
            if not thickness_match:
                raise ClarificationRequiredError("What wall thickness should I use? Give a measurement in mm.")
            thickness = float(thickness_match.group(1))
            result = self._hollow_mesh(mesh, thickness)
            return EditResult(result, "geometry", f"Hollowed the mesh with an inward {thickness:g} mm offset.", [f"hollow walls {thickness:g} mm"])

        cut_match = re.search(r"(?:cut|trim)\s+(\d+(?:\.\d+)?)\s*mm\s*(?:off|from)\s+(?:the\s+)?bottom", lowered)
        if "cut" in lowered or "trim" in lowered:
            if not cut_match:
                raise ClarificationRequiredError("Specify how many mm to cut and which side or plane.")
            amount = float(cut_match.group(1))
            z_min = float(mesh.bounds[0][2])
            tool = trimesh.creation.box(extents=(float(mesh.extents[0]) * 2, float(mesh.extents[1]) * 2, amount))
            tool.apply_translation((float(mesh.centroid[0]), float(mesh.centroid[1]), z_min + amount / 2))
            result = self._boolean(mesh, tool, "difference")
            return EditResult(result, "geometry", f"Cut {amount:g} mm from the bottom.", [f"cut bottom {amount:g} mm"])

        handle = re.search(r"(?:add\s+)?(?:a\s+)?(\d+(?:\.\d+)?)\s*mm\s+handle", lowered)
        if "handle" in lowered:
            if not handle:
                raise ClarificationRequiredError("What outside diameter should the loop handle be? Give a measurement in mm.")
            diameter = float(handle.group(1))
            major, minor = diameter * 0.38, diameter * 0.12
            tool = trimesh.creation.torus(major_radius=major, minor_radius=minor, major_sections=48, minor_sections=12)
            extents = mesh.extents
            tool.apply_translation((float(mesh.bounds[1][0]) + major * 0.75, float(mesh.centroid[1]), float(mesh.centroid[2])))
            result = self._boolean(mesh, tool, "union")
            return EditResult(result, "geometry", f"Added a loop handle with {diameter:g} mm outside diameter.", [f"handle {diameter:g} mm"])

        if "base" in lowered:
            remove_base = re.search(r"\b(remove|delete)\b", lowered)
            if remove_base:
                recorded_thickness = (feature_metadata or {}).get("editor_base_thickness_mm")
                if recorded_thickness:
                    z_min = float(mesh.bounds[0][2])
                    overlap = float((feature_metadata or {}).get("editor_base_overlap_mm", 0))
                    base_depth = float(recorded_thickness) - overlap
                    cutter_depth = base_depth + 0.02
                    cutter = trimesh.creation.box(extents=(float(mesh.extents[0]) * 2, float(mesh.extents[1]) * 2, cutter_depth))
                    bounds_center = mesh.bounding_box.centroid
                    cutter.apply_translation((float(bounds_center[0]), float(bounds_center[1]), z_min + base_depth - cutter_depth / 2))
                    result = self._boolean(mesh, cutter, "difference")
                    return EditResult(result, "geometry", "Removed the recorded editor-added base.", ["remove base"], {"remove_editor_base": True})
                raise UnsupportedEditError("No recorded editor-added base was found to remove. Use Undo if the base was added in this session.")
            if not mesh.is_watertight:
                raise UnsupportedEditError("Adding a base requires a watertight source mesh.")
            thickness_match = re.search(r"(\d+(?:\.\d+)?)\s*mm\s*(?:base|thick|thickness)", lowered)
            if not thickness_match:
                raise ClarificationRequiredError("What thickness should the base be? Give a measurement in mm.")
            thickness = float(thickness_match.group(1))
            overlap = min(0.5, thickness * 0.1)
            tool = trimesh.creation.box(extents=(float(mesh.extents[0]) * 0.9, float(mesh.extents[1]) * 0.9, thickness))
            bounds_center = mesh.bounding_box.centroid
            tool.apply_translation((float(bounds_center[0]), float(bounds_center[1]), float(mesh.bounds[0][2]) - thickness / 2 + overlap))
            result = self._boolean(mesh, tool, "union")
            return EditResult(result, "geometry", f"Added a {thickness:g} mm base.", [f"add base {thickness:g} mm"], {"editor_base_thickness_mm": thickness, "editor_base_overlap_mm": overlap})

        if not feature_request:
            return None
        if "base" not in lowered:
            raise UnsupportedEditError(
                "This editor currently supports adding or removing a base. Holes, handles, and freeform parts require a configured generative editing provider."
            )
        raise UnsupportedEditError("Unsupported feature edit.")


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
        for match in re.finditer(rf"(\d+(?:\.\d+)?)\s*mm\s*\b({dimension_words})\b", text):
            target, word = float(match.group(1)), match.group(2)
            axis = self.axis_names[word]
            operations.append(StructuredOperation("set_dimension", axis, target, f"set {self._axis_label(axis)} to {target:g} mm"))

        for match in re.finditer(rf"increase\s+(?:the\s+|its\s+)?({dimension_words})\s+by\s+(\d+(?:\.\d+)?)\s*(%|mm)", text):
            word, amount, unit = match.group(1), float(match.group(2)), match.group(3)
            axis = self.axis_names[word]
            kind = "scale_axis" if unit == "%" else "increase_dimension"
            value = 1 + amount / 100 if unit == "%" else amount
            operations.append(StructuredOperation(kind, axis, value, f"increase {self._axis_label(axis)} by {amount:g}{unit}"))

        for match in re.finditer(rf"(?:make|increase)\s+(?:it\s+|the\s+|its\s+)?(\d+(?:\.\d+)?)\s*mm\s+(wider|deeper|taller)", text):
            amount, adjective = float(match.group(1)), match.group(2)
            axis = {"wider": 0, "deeper": 1, "taller": 2}[adjective]
            operations.append(StructuredOperation("increase_dimension", axis, amount, f"increase {self._axis_label(axis)} by {amount:g}mm"))

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

    def apply(self, mesh: trimesh.Trimesh, prompt: str, scale_status: str = "unknown", feature_metadata: dict | None = None) -> EditResult:
        text = prompt.strip()
        if not text:
            raise UnsupportedEditError("Enter an editing instruction.")
        feature_result = self.features.apply(mesh, text, scale_status=scale_status, feature_metadata=feature_metadata)
        if feature_result:
            return feature_result

        result = mesh.copy()
        intent = self.interpreter.interpret(result, text)
        physical_operations = {"set_dimension", "increase_dimension", "translate"}
        if scale_status != "calibrated" and any(operation.kind in physical_operations for operation in intent.operations):
            raise ClarificationRequiredError("Calibrate the model with one known measurement before using millimeter dimensions or positions.")
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
            return EditResult(result, "visual_only", f"Changed the preview material to {color}; STL geometry is unchanged.", descriptions, feature_metadata or {})
        return EditResult(result, "geometry", "; ".join(descriptions).capitalize() + ".", descriptions)


def validate_for_print(mesh: trimesh.Trimesh, scale_status: str = "unknown") -> dict:
    extents = [round(float(value), 2) for value in mesh.extents]
    parts = list(mesh.split(only_watertight=False))
    volume_orientation = 1 if mesh.volume >= 0 else -1
    body_count = sum(1 for part in parts if float(part.volume) * volume_orientation > 1e-12)
    edges, edge_counts = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    nonmanifold_edges = int(np.count_nonzero(edge_counts > 2))
    boundary_edges = int(np.count_nonzero(edge_counts == 1))
    face_area = np.asarray(mesh.area_faces)
    degenerate_faces = int(np.count_nonzero((face_area <= 1e-12) | (mesh.faces[:, 0] == mesh.faces[:, 1]) | (mesh.faces[:, 1] == mesh.faces[:, 2]) | (mesh.faces[:, 0] == mesh.faces[:, 2])))
    warnings: list[str] = []
    if not mesh.is_watertight:
        warnings.append("Mesh is not watertight and may need repair before printing.")
    if not mesh.is_winding_consistent:
        warnings.append("Mesh face winding is inconsistent.")
    if nonmanifold_edges:
        warnings.append(f"Mesh has {nonmanifold_edges} non-manifold edges.")
    if degenerate_faces:
        warnings.append(f"Mesh has {degenerate_faces} degenerate faces.")
    if scale_status == "calibrated" and min(extents) < 1:
        warnings.append("One dimension is under 1 mm and may be too thin to print.")
    if body_count > 1:
        warnings.append("Mesh contains multiple disconnected solid bodies.")
    if scale_status != "calibrated":
        warnings.append("Physical dimensions are unknown until the model is calibrated with a real measurement.")
    warnings.append("Minimum feature or wall thickness has not been measured; inspect or slice the model before printing.")
    return {
        "watertight": bool(mesh.is_watertight),
        "mesh_integrity": {
            "winding_consistent": bool(mesh.is_winding_consistent),
            "body_count": body_count,
            "surface_component_count": len(parts),
            "nonmanifold_edges": nonmanifold_edges,
            "boundary_edges": boundary_edges,
            "degenerate_faces": degenerate_faces,
            "vertices": int(len(mesh.vertices)),
            "faces": int(len(mesh.faces)),
        },
        "scale_status": scale_status,
        "dimensions_mm": {"width": extents[0], "depth": extents[1], "height": extents[2]} if scale_status == "calibrated" else None,
        "dimensions_model_units": {"width": extents[0], "depth": extents[1], "height": extents[2]} if scale_status != "calibrated" else None,
        "minimum_feature_thickness_mm": None,
        "minimum_feature_thickness_status": "not_measured",
        "warnings": warnings,
    }
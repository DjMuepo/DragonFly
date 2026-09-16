from pathlib import Path
import trimesh

from app.mesh_factory import export_glb

out = Path('/tmp/eye-geometry-test')
name, path = export_glb(
	'cylinder',
	out,
	prompt='make a cylinder 100 mm tall, make it 20% wider, add a hole, and round the edges',
)
assert path.exists(), path
assert path.stat().st_size > 1000, path.stat().st_size
assert path.with_suffix('.stl').exists()
mesh = trimesh.load(path, force='mesh')
assert mesh.is_watertight
assert max(abs(float(value)) for value in mesh.bounding_box.centroid) < 0.001
assert round(float(mesh.extents[2])) == 100
print({'model': name, 'bytes': path.stat().st_size, 'extents_mm': mesh.extents.tolist()})

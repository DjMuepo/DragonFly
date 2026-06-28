from pathlib import Path
from app.mesh_factory import export_glb

out = Path('/tmp/eye-geometry-test')
name, path = export_glb('spray bottle', out)
assert path.exists(), path
assert path.stat().st_size > 1000, path.stat().st_size
print({'model': name, 'bytes': path.stat().st_size})

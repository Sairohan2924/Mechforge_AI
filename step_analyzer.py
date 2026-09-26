from __future__ import annotations
from pathlib import Path
import math


def _vec(v):
    return (float(v.x), float(v.y), float(v.z))


def analyze_cad_file(filename: str, data: bytes):
    suffix=Path(filename).suffix.lower()
    tmp=Path('._mechforge_model'+suffix)
    tmp.write_bytes(data)
    try:
        if suffix in {'.step','.stp'}:
            return _analyze_step(tmp)
        if suffix=='.stl':
            return _analyze_stl(tmp)
        raise ValueError('Unsupported CAD format')
    finally:
        try: tmp.unlink()
        except Exception: pass


def _analyze_step(path: Path):
try:
    import cadquery as cq
except Exception as e:
    print(
        f"MECHFORGE CADQUERY IMPORT ERROR: "
        f"{type(e).__name__}: {e}",
        flush=True
    )
    raise RuntimeError(
        f"CadQuery import failed: {type(e).__name__}: {e}"
    ) from e
    wp=cq.importers.importStep(str(path))
    solids=wp.solids().vals()
    if not solids: raise ValueError('No solid bodies were found in the STEP file.')
    bb=wp.val().BoundingBox()
    volume=sum(float(s.Volume()) for s in solids)
    area=sum(float(s.Area()) for s in solids)
    faces=sum(len(s.Faces()) for s in solids)
    edges=sum(len(s.Edges()) for s in solids)
    vertices=sum(len(s.Vertices()) for s in solids)
    verts=[]; tris=[]; offset=0
    for s in solids:
        vs, ts=s.tessellate(0.35)
        verts.extend([_vec(v) for v in vs])
        tris.extend([(a+offset,b+offset,c+offset) for a,b,c in ts])
        offset += len(vs)
    return {
        'format':'STEP','solids':len(solids),'faces':faces,'edges':edges,'vertices':vertices,
        'bbox':{'x':bb.xlen,'y':bb.ylen,'z':bb.zlen},'volume_mm3':volume,'surface_area_mm2':area,
        'mesh':{'vertices':verts,'triangles':tris},
        'derived':_derived_dfm(bb.xlen,bb.ylen,bb.zlen,volume,faces,edges)
    }


def _analyze_stl(path: Path):
    import trimesh
    mesh=trimesh.load(str(path), force='mesh')
    if hasattr(mesh,'geometry'):
        mesh=trimesh.util.concatenate(tuple(mesh.geometry.values()))
    ext=mesh.extents
    verts=mesh.vertices.tolist(); tris=mesh.faces.tolist()
    return {'format':'STL','solids':1,'faces':int(len(mesh.faces)),'edges':int(len(mesh.edges_unique)),'vertices':int(len(mesh.vertices)),
            'bbox':{'x':float(ext[0]),'y':float(ext[1]),'z':float(ext[2])},'volume_mm3':abs(float(mesh.volume)),'surface_area_mm2':float(mesh.area),
            'mesh':{'vertices':verts,'triangles':tris},
            'derived':_derived_dfm(float(ext[0]),float(ext[1]),float(ext[2]),abs(float(mesh.volume)),len(mesh.faces),len(mesh.edges_unique))}


def _derived_dfm(x,y,z,volume,faces,edges):
    dims=sorted([x,y,z], reverse=True)
    aspect=dims[0]/max(dims[1],0.001)
    return {'overall_size_mm':dims,'aspect_ratio':aspect,'compactness':volume/max(x*y*z,0.001),
            'complexity_faces':faces,'complexity_edges':edges,
            'notes':['Geometry is measured from the uploaded CAD solid.','STEP analysis uses OCCT/CadQuery tessellation for visualization.',
                     'CAD-derived geometry complements drawing-derived tolerances; it does not infer missing functional requirements.']}

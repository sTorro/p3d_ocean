# -*- coding: utf-8 -*-

"""
Filename: ocean_geometry.py
Author: storro
Date: 2026-02-11
Description: Procedurally generate a subdivided plane mesh for ocean rendering
             The grid is centered at the origin, with UVs tiled across it
"""

from panda3d.core import (
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
)


def make_ocean_grid(
    grid_size: float = 200.0,
    grid_subdiv: int = 256,
    uv_tiles: float = 1.0,
) -> NodePath:
    """
    Generate a subdivided plane mesh for ocean rendering
    """

    if grid_subdiv < 1:
        raise ValueError("grid_subdiv must be >= 1")

    verts_per_side = grid_subdiv + 1
    vertex_count = verts_per_side * verts_per_side

    fmt = GeomVertexFormat.get_v3n3t2()
    vdata = GeomVertexData("ocean", fmt, Geom.UH_static)
    vdata.set_num_rows(vertex_count)

    vw_pos = GeomVertexWriter(vdata, "vertex")
    vw_nrm = GeomVertexWriter(vdata, "normal")
    vw_uv = GeomVertexWriter(vdata, "texcoord")

    half = grid_size * 0.5
    step = grid_size / grid_subdiv

    for j in range(verts_per_side):
        v = (j / grid_subdiv) * uv_tiles
        y = -half + j * step
        for i in range(verts_per_side):
            u = (i / grid_subdiv) * uv_tiles
            x = -half + i * step

            vw_pos.add_data3f(x, y, 0.0)
            vw_nrm.add_data3f(0.0, 0.0, 1.0)
            vw_uv.add_data2f(u, v)

    tris = GeomTriangles(Geom.UH_static)
    for j in range(grid_subdiv):
        row0 = j * verts_per_side
        row1 = (j + 1) * verts_per_side
        for i in range(grid_subdiv):
            i0 = row0 + i
            i1 = row0 + i + 1
            i2 = row1 + i
            i3 = row1 + i + 1

            # Two triangles per quad
            # Winding order chosen so the front-face points +Z (visible from above)
            tris.add_vertices(i0, i1, i2)
            tris.close_primitive()
            tris.add_vertices(i1, i3, i2)
            tris.close_primitive()

    geom = Geom(vdata)
    geom.add_primitive(tris)

    node = GeomNode("ocean")
    node.add_geom(geom)

    return NodePath(node)

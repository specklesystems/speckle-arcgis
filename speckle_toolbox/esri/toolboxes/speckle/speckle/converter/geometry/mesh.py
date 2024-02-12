from datetime import datetime
import os
from typing import List
import arcpy
import math

from specklepy.objects.geometry import Mesh, Point, Polyline
from specklepy.objects.other import RenderMaterial
from specklepy.objects.GIS.geometry import GisPolygonGeometry

import inspect

import shapefile
from shapefile import TRIANGLE_STRIP, TRIANGLE_FAN, OUTER_RING


from speckle.speckle.converter.layers.utils import get_scale_factor, getDisplayValueList
from speckle.speckle.converter.geometry.point import pointToNative
from speckle.speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.speckle.converter.layers.utils import get_scale_factor
from speckle.speckle.utils.panel_logging import logToUser
from speckle.speckle.plugin_utils.helpers import findOrCreatePath

from panda3d.core import Triangulator

from speckle.speckle.converter.geometry.utils import apply_pt_transform_matrix


def meshToNative(meshes: Mesh, sr, dataStorage=None):
    """Converts a Speckle Mesh to MultiPatch"""
    from speckle.speckle.converter.geometry.conversions import multiPolygonToNative

    result = []

    print("06___________________Mesh to Native")
    new_path = writeMeshToShp(meshes, "", dataStorage)

    cursor = arcpy.da.SearchCursor(new_path, "Speckle_ID")
    class_shapes = [shp_id[0] for n, shp_id in enumerate(cursor)]
    del cursor
    return class_shapes[0]

    for m in meshes:
        if isinstance(m, Mesh):
            faces, _ = deconstructSpeckleMesh(m)
            for face in faces:
                flat_list = []
                for xs in face:
                    for x in xs:
                        flat_list.append(x)
                poly = Polyline().from_list(flat_list)
                poly.closed = True

                polygon = GisPolygonGeometry(
                    boundary=poly, units=m.units, displayValue=[]
                )
                result.append(multiPolygonToNative([polygon], sr, dataStorage))

    return result


def writeMeshToShp(meshes: List[Mesh], path: str, dataStorage):
    """Converts a Speckle Mesh to native geometry"""
    print("06___________________Mesh to Native SHP")
    try:
        try:
            if path == "":
                path = (
                    os.path.expandvars(r"%LOCALAPPDATA%")
                    + "\\Temp\\Speckle_ArcGIS_temp\\"
                    + datetime.now().strftime("%Y-%m-%d_%H-%M")
                )
                findOrCreatePath(path)
            w = shapefile.Writer(path)  # + "\\" + str(meshes[0].id))
        except Exception as e:
            logToUser(e)
            return

        w.field("speckle_id", "C")

        for _, geom in enumerate(meshes):
            meshList: List = getDisplayValueList(geom)
            w = fill_multi_mesh_parts(w, meshList, geom.id, dataStorage)
        w.close()
        return path

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def fill_multi_mesh_parts(
    w: shapefile.Writer, meshes: List[Mesh], geom_id: str, dataStorage
):
    try:
        parts_list = []
        types_list = []
        for mesh in meshes:
            if not isinstance(mesh, Mesh):
                continue
            try:
                # print(f"Fill multi-mesh parts # {geom_id}")
                parts_list_x, types_list_x = deconstructSpeckleMesh(mesh, dataStorage)
                parts_list.extend(parts_list_x)
                types_list.extend(types_list_x)
            except Exception as e:
                pass

        w.multipatch(parts_list, partTypes=types_list)  # one type for each part
        w.record(geom_id)
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return w


def fill_mesh_parts(w: shapefile.Writer, mesh: Mesh, geom_id: str, dataStorage):

    try:
        # print(f"Fill mesh parts # {geom_id}")
        parts_list, types_list = deconstructSpeckleMesh(mesh, dataStorage)
        w.multipatch(parts_list, partTypes=types_list)  # one type for each part
        w.record(geom_id)

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return w


def deconstructSpeckleMesh(mesh: Mesh, dataStorage):
    parts_list = []
    types_list = []
    try:
        scale = get_scale_factor(mesh.units)

        count = 0  # sequence of vertex (not of flat coord list)
        for f in mesh.faces:  # real number of loops will be at least 3 times less
            try:
                vertices = mesh.faces[count]
                if mesh.faces[count] == 0:
                    vertices = 3
                if mesh.faces[count] == 1:
                    vertices = 4

                face = []
                for i in range(vertices):
                    index_faces = count + 1 + i
                    index_vertices = mesh.faces[index_faces] * 3
                    pt_coords = [
                        mesh.vertices[index_vertices],
                        mesh.vertices[index_vertices + 1],
                        mesh.vertices[index_vertices + 2],
                    ]
                    pt_coords_new = apply_pt_transform_matrix(pt_coords, dataStorage)
                    face.append([scale * coord for coord in pt_coords_new])

                parts_list.append(face)
                types_list.append(OUTER_RING)
                count += vertices + 1
            except:
                break  # when out of range

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return parts_list, types_list


def constructMeshFromRaster(vertices, faces, colors):
    mesh = None
    try:
        mesh = Mesh.create(vertices, faces, colors)
        mesh.units = "m"
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return mesh


def constructMesh(vertices, faces, colors):
    mesh = None
    try:
        mesh = Mesh.create(vertices, faces, colors)
        mesh.units = "m"
        material = RenderMaterial()
        material.diffuse = colors[0]
        mesh.renderMaterial = material
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return mesh


def meshPartsFromPolygon(
    polyBorder: List[Point],
    voidsAsPts: List[List[Point]],
    existing_vert: int,
    index: int,
    layer,
    dataStorage,
):

    try:
        # print("__meshPartsFromPolygon__")
        vertices = []
        total_vertices = 0
        # print(layer)
        try:
            sr = arcpy.Describe(layer.dataSource).spatialReference
        except Exception as e:
            print(e)
            sr = None
        # print(sr)
        coef = 1
        maxPoints = 5000
        if len(polyBorder) >= maxPoints:
            coef = int(len(polyBorder) / maxPoints)

        if (
            len(voidsAsPts) == 0
        ):  # only if there is a mesh with no voids and large amount of points
            # print("mesh with no voids")
            for k, ptt in enumerate(polyBorder):  # pointList:
                pt = polyBorder[k * coef]
                if k < maxPoints:
                    # if isinstance(pt, QgsPointXY):
                    #    pt = QgsPoint(pt)
                    # print(pt)
                    if isinstance(pt, Point):
                        x = pt.x
                        y = pt.y
                        z = pt.z
                        # pt = pointToNative(pt, sr, dataStorage).getPart()
                    else:
                        x = pt.X
                        y = pt.Y
                        z = 0 if math.isnan(pt.Z) else pt.Z
                    vertices.extend([x, y, z])
                    total_vertices += 1
                else:
                    break

            ran = range(0, total_vertices)
            faces = [total_vertices]
            faces.extend([i + existing_vert for i in ran])
            # else: https://docs.panda3d.org/1.10/python/reference/panda3d.core.Triangulator
        else:  # if there are voids
            print("mesh with voids")
            # if its a large polygon with voids to be triangualted, lower the coef even more:
            maxPoints = 100
            if len(polyBorder) >= maxPoints:
                coef = int(len(polyBorder) / maxPoints)

            trianglator = Triangulator()
            faces = []

            pt_count = 0
            # add extra middle point for border
            for k, ptt in enumerate(polyBorder):  # pointList:
                pt = polyBorder[k * coef]
                if k < maxPoints:
                    if pt_count < len(polyBorder) - 1 and k < (maxPoints - 1):
                        pt2 = polyBorder[(k + 1) * coef]
                    else:
                        pt2 = polyBorder[0]

                    trianglator.addPolygonVertex(trianglator.addVertex(pt.x, pt.y))
                    vertices.extend([pt.x, pt.y, pt.z])
                    trianglator.addPolygonVertex(
                        trianglator.addVertex((pt.x + pt2.x) / 2, (pt.y + pt2.y) / 2)
                    )
                    vertices.extend(
                        [(pt.x + pt2.x) / 2, (pt.y + pt2.y) / 2, (pt.z + pt2.z) / 2]
                    )
                    total_vertices += 2
                    pt_count += 1
                else:
                    break

            # add void points
            for pts in voidsAsPts:
                trianglator.beginHole()

                coefVoid = 1
                if len(pts) >= maxPoints:
                    coefVoid = int(len(pts) / maxPoints)
                for k, ptt in enumerate(pts):
                    pt = pts[k * coefVoid]
                    if k < maxPoints:
                        trianglator.addHoleVertex(trianglator.addVertex(pt.x, pt.y))
                        vertices.extend([pt.x, pt.y, pt.z])
                        total_vertices += 1
                    else:
                        break

            trianglator.triangulate()
            i = 0
            # print(trianglator.getNumTriangles())
            while i < trianglator.getNumTriangles():
                tr = [
                    trianglator.getTriangleV0(i),
                    trianglator.getTriangleV1(i),
                    trianglator.getTriangleV2(i),
                ]
                faces.extend(
                    [
                        3,
                        tr[0] + existing_vert,
                        tr[1] + existing_vert,
                        tr[2] + existing_vert,
                    ]
                )
                i += 1
            ran = range(0, total_vertices)

        # print("color")
        col = featureColorfromNativeRenderer(index, layer)  # (100<<16) + (100<<8) + 100
        colors = [col for i in ran]  # apply same color for all vertices

        return total_vertices, vertices, faces, colors
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None, None, None, None

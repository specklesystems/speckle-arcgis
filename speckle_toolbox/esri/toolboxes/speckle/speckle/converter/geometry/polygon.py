from typing import List, Sequence, Union
import arcpy
import json
from arcpy.arcobjects.arcobjects import SpatialReference

from specklepy.objects import Base
from specklepy.objects.geometry import Point, Arc, Circle, Polycurve, Polyline, Line

import inspect

from speckle.speckle.converter.geometry.mesh import (
    constructMesh,
    constructMeshFromRaster,
    meshPartsFromPolygon,
)
from speckle.speckle.converter.geometry.point import pointToCoord, pointToNative
from speckle.speckle.converter.layers.symbology import featureColorfromNativeRenderer
from speckle.speckle.converter.geometry.polyline import (
    polylineFromVerticesToSpeckle,
    speckleArcCircleToPoints,
    curveToSpeckle,
)
from speckle.speckle.converter.geometry.utils import (
    speckleBoundaryToSpecklePts,
    specklePolycurveToPoints,
)
from speckle.speckle.utils.panel_logging import logToUser

import math
from panda3d.core import Triangulator


def polygonToSpeckleMesh(geom, index: int, layer, multitype: bool):
    print("________polygonToSpeckleMesh_____")
    print(geom)
    polygon = Base(units="m")
    try:

        vertices = []
        faces = []
        colors = []
        existing_vert = 0

        for i, p in enumerate(geom):
            # print("____start enumerate feature")
            # print(p) #<geoprocessing array object object at 0x0000026796C77110>
            print(p)
            boundary, voids = getPolyBoundaryVoids(p, layer, multitype)
            # print(boundary)
            # print(voids)
            polyBorder = speckleBoundaryToSpecklePts(boundary)
            # print(polyBorder)
            voidsAsPts = []
            for v in voids:
                pts = speckleBoundaryToSpecklePts(v)
                voidsAsPts.append(pts)
            # print(voidsAsPts)
            # print("__to start meshPartsFromPolygon")
            total_vert, vertices_x, faces_x, colors_x = meshPartsFromPolygon(
                polyBorder, voidsAsPts, existing_vert, index, layer
            )

            existing_vert += total_vert
            vertices.extend(vertices_x)
            faces.extend(faces_x)
            colors.extend(colors_x)

        # print("Colors: ")
        # print(colors)
        mesh = constructMesh(vertices, faces, colors)
        if mesh is not None:
            polygon.displayValue = [mesh]
        else:
            logToUser(
                "Mesh creation from Polygon failed. Boundaries will be used as displayValue",
                level=1,
                func=inspect.stack()[0][3],
            )
        return polygon

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None


def getPolyBoundaryVoids(geom, layer, multiType: bool):
    # print("__getPolyBoundaryVoids__")
    voids: List[Union[None, Polyline, Arc, Line, Polycurve]] = []
    # print(voids)
    boundary = None
    pointList = []
    try:
        # partsBoundaries = []
        # partsVoids = []
        if multiType is False:  # Multipolygon
            try:  # might be no property "has curves"
                if geom.hasCurves:
                    print("has curves")
                    # geometry SHAPE@ tokens: https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/reading-geometries.htm
                    print(geom.JSON)
                    boundary = curveToSpeckle(geom, "Polygon", geom, layer)
                else:
                    print("no curves")
                    for p in geom:
                        for pt in p:
                            # print(pt)
                            if pt != None:
                                pointList.append(pt)
                    boundary = polylineFromVerticesToSpeckle(
                        pointList, True, geom, layer
                    )
                    print(boundary)
            except:  # for multipatches, no property "has curves"
                # print("multipatch")
                for pt in geom:
                    # print(pt)
                    if pt != None:
                        pointList.append(pt)
                boundary = polylineFromVerticesToSpeckle(pointList, True, geom, layer)
                # print(boundary)
            # partsBoundaries.append(boundary)
            # partsVoids.append([])

        else:
            print("multi type")
            for i, p in enumerate(geom):
                print(p)
                for pt in p:
                    # print(pt) # 284394.58100903 5710688.11602606 NaN NaN
                    if pt == None and boundary == None:  # first break
                        boundary = polylineFromVerticesToSpeckle(
                            pointList, True, geom, layer
                        )
                        pointList = []
                    elif pt == None and boundary != None:  # breaks btw voids
                        void = polylineFromVerticesToSpeckle(
                            pointList, True, geom, layer
                        )
                        voids.append(void)
                        pointList = []
                    elif pt != None:  # add points to whatever list (boundary or void)
                        pointList.append(pt)

                if boundary != None and len(pointList) > 0:  # remaining polyline
                    void = polylineFromVerticesToSpeckle(pointList, True, geom, layer)
                    voids.append(void)

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return boundary, voids


def multiPolygonToSpeckle(geom, index: str, layer, multiType: bool):

    print("___MultiPolygon to Speckle____")
    polygon = []
    try:
        # print(enumerate(geom.getPart())) # this method ignores curvature and voids
        # print(json.loads(geom.JSON))
        # js = json.loads(geom.JSON)['rings']
        # https://desktop.arcgis.com/en/arcmap/latest/analyze/python/reading-geometries.htm
        for i, x in enumerate(geom):  # [[x,x,x]
            print("Part # " + str(i + 1))
            print(x)
            boundaryFinished = 0
            arrBoundary = []
            arrInnerRings = []
            for ptn in x:  # arcpy.Point
                if ptn is None:
                    boundaryFinished += 1
                    arrInnerRings.append([])  # start of new Inner Ring
                elif boundaryFinished == 0 and ptn is not None:
                    arrBoundary.append(ptn)
                elif boundaryFinished == 1 and ptn is not None:
                    arrInnerRings[len(arrInnerRings) - 1].append(ptn)

            full_arr = [arrBoundary] + arrInnerRings
            # print(full_arr)
            poly = arcpy.Polygon(
                arcpy.Array(full_arr),
                arcpy.Describe(layer.dataSource).SpatialReference,
                has_z=True,
            )
            # print(poly) #<geoprocessing describe geometry object object at 0x000002B2D3E338D0>
            polygon.append(polygonToSpeckle(poly, index, layer, poly.isMultipart))

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return polygon


def polygonToSpeckle(geom, index: int, layer, multitype: bool, dataStorage):
    """Converts a Polygon to Speckle"""
    polygon = Base(units="m")
    try:
        print("___Polygon to Speckle____")
        print(geom)

        boundary, voids = getPolyBoundaryVoids(geom, layer, multitype)

        data = arcpy.Describe(layer.dataSource)
        sr = data.spatialReference

        if boundary is None:
            return None
        polygon.boundary = boundary
        polygon.voids = voids
        polygon.displayValue = [boundary] + voids
        # print(boundary)

        ############# mesh
        vertices = []
        polyBorder = []
        total_vertices = 0
        if isinstance(boundary, Circle) or isinstance(boundary, Arc):
            polyBorder = speckleArcCircleToPoints(boundary)
        elif isinstance(boundary, Polycurve):
            polyBorder = specklePolycurveToPoints(boundary)
            # polygon.boundary.displayValue.closed = True
        elif isinstance(boundary, Line):
            pass
        elif isinstance(boundary, Polyline):
            try:
                polyBorder = boundary.as_points()
            except:
                pass  # if Line
        # print(polyBorder)

        if len(polyBorder) > 2:  # at least 3 points
            print("make meshes from polygons")
            if len(voids) == 0:  # if there is a mesh with no voids
                for pt in polyBorder:
                    if isinstance(pt, Point):
                        pt = pointToNative(pt, sr, dataStorage).getPart()  # SR unknown
                    x = pt.X
                    y = pt.Y
                    z = 0 if math.isnan(pt.Z) else pt.Z
                    vertices.extend([x, y, z])
                    total_vertices += 1
                # print(vertices)
                ran = range(0, total_vertices)
                faces = [total_vertices]
                faces.extend([i for i in ran])
                # print(faces)
                # else: https://docs.panda3d.org/1.10/python/reference/panda3d.core.Triangulator
            else:
                trianglator = Triangulator()
                faces = []

                # add boundary points
                # polyBorder = boundary.as_points()
                pt_count = 0
                # add extra middle point for border
                for pt in polyBorder:
                    if pt_count < len(polyBorder) - 1:
                        pt2 = polyBorder[pt_count + 1]
                    else:
                        pt2 = polyBorder[0]

                    trianglator.addPolygonVertex(trianglator.addVertex(pt.x, pt.y))
                    vertices.extend([pt.x, pt.y, pt.z])

                    # trianglator.addPolygonVertex(trianglator.addVertex((pt.x+pt2.x)/4*3, (pt.y+pt2.y)/4*3))
                    # vertices.extend([(pt.x+pt2.x)/4*3, (pt.y+pt2.y)/4*3, (pt.z+pt2.z)/4*3])

                    trianglator.addPolygonVertex(
                        trianglator.addVertex((pt.x + pt2.x) / 2, (pt.y + pt2.y) / 2)
                    )
                    vertices.extend(
                        [(pt.x + pt2.x) / 2, (pt.y + pt2.y) / 2, (pt.z + pt2.z) / 2]
                    )

                    # trianglator.addPolygonVertex(trianglator.addVertex((pt.x+pt2.x)/4, (pt.y+pt2.y)/4))
                    # vertices.extend([(pt.x+pt2.x)/4, (pt.y+pt2.y)/4, (pt.z+pt2.z)/4])

                    total_vertices += 2
                    pt_count += 1

                # add void points
                for i in range(len(voids)):
                    trianglator.beginHole()

                    pts = []
                    if isinstance(voids[i], Circle) or isinstance(voids[i], Arc):
                        pts = speckleArcCircleToPoints(voids[i])
                    elif isinstance(voids[i], Polycurve):
                        pts = specklePolycurveToPoints(voids[i])
                    elif isinstance(voids[i], Line):
                        pass
                    else:
                        try:
                            pts = voids[i].as_points()
                        except:
                            pass  # if Line
                    # pts = voids[i].as_points()
                    for pt in pts:
                        trianglator.addHoleVertex(trianglator.addVertex(pt.x, pt.y))
                        vertices.extend([pt.x, pt.y, pt.z])
                        total_vertices += 1

                trianglator.triangulate()
                i = 0
                while i < trianglator.getNumTriangles():
                    tr = [
                        trianglator.getTriangleV0(i),
                        trianglator.getTriangleV1(i),
                        trianglator.getTriangleV2(i),
                    ]
                    faces.extend([3, tr[0], tr[1], tr[2]])
                    i += 1
                ran = range(0, total_vertices)

            # print(polygon)
            col = featureColorfromNativeRenderer(index, layer)
            colors = [col for i in ran]  # apply same color for all vertices
            mesh = constructMesh(vertices, faces, colors)

            if mesh is not None:
                polygon.displayValue = [mesh]
            else:
                logToUser(
                    "Mesh creation from Polygon failed. Boundaries will be used as displayValue",
                    level=1,
                    func=inspect.stack()[0][3],
                )
            return polygon
        else:
            logToUser(
                "Not enough points for Polygon boundary",
                level=1,
                func=inspect.stack()[0][3],
            )
            return None

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None


def polygonToNative(poly: Base, sr: arcpy.SpatialReference, dataStorage) -> arcpy.Polygon:
    """Converts a Speckle Polygon base object to QgsPolygon.
    This object must have a 'boundary' and 'voids' properties.
    Each being a Speckle Polyline and List of polylines respectively."""

    print("_______Drawing polygons____")
    polygon = None
    try:
        try:
            poly = poly["geometry"]
        except:
            pass
        # pts = [pointToCoord(pt) for pt in poly["boundary"].as_points()]
        pointsSpeckle = []
        if isinstance(poly["boundary"], Circle) or isinstance(poly["boundary"], Arc):
            pointsSpeckle = speckleArcCircleToPoints(poly["boundary"])
        elif isinstance(poly["boundary"], Polycurve):
            pointsSpeckle = specklePolycurveToPoints(poly["boundary"])
        elif isinstance(poly["boundary"], Line):
            pass
        else:
            try:
                pointsSpeckle = poly["boundary"].as_points()
            except:
                pass  # if Line

        pts = [pointToCoord(pt) for pt in pointsSpeckle]
        # print(pts)

        outer_arr = [arcpy.Point(*coords) for coords in pts]
        outer_arr.append(outer_arr[0])
        geomPart = []
        try:
            for void in poly["voids"]:
                # print(void)
                # pts = [pointToCoord(pt) for pt in void.as_points()]
                pointsSpeckle = []
                if isinstance(void, Circle) or isinstance(void, Arc):
                    pointsSpeckle = speckleArcCircleToPoints(void)
                elif isinstance(void, Polycurve):
                    pointsSpeckle = specklePolycurveToPoints(void)
                elif isinstance(void, Line):
                    pass
                else:
                    try:
                        pointsSpeckle = void.as_points()
                    except:
                        pass  # if Line
                pts = [pointToCoord(pt) for pt in pointsSpeckle]

                inner_arr = [arcpy.Point(*coords) for coords in pts]
                inner_arr.append(inner_arr[0])
                geomPart.append(arcpy.Array(inner_arr))
        except:
            pass
        geomPart.insert(0, outer_arr)
        geomPartArray = arcpy.Array(geomPart)
        polygon = arcpy.Polygon(geomPartArray, sr, has_z=True)

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return polygon

from regex import F
from specklepy.objects import Base
from specklepy.objects.geometry import (
    Line,
    Mesh,
    Point,
    Polyline,
    Curve,
    Arc,
    Circle,
    Polycurve,
    Ellipse,
)

import arcpy
from typing import Any, List, Tuple, Union, Sequence

import inspect
from specklepy.objects.GIS.geometry import (
    GisLineElement,
    GisPointElement,
    GisPolygonElement,
)
from specklepy.objects.GIS.geometry import GisPolygonGeometry

from speckle.speckle.converter.geometry.mesh import meshToNative
from speckle.speckle.converter.geometry.polygon import (
    polygonToNative,
    multiPolygonToNative,
    polygonToSpeckle,
    multiPolygonToSpeckle,
    polygonToSpeckleMesh,
)
from speckle.speckle.converter.geometry.utils import (
    specklePolycurveToPoints,
    addCorrectUnits,
)
from speckle.speckle.converter.geometry.polyline import (
    anyLineToSpeckle,
    arcToNative,
    ellipseToNative,
    circleToNative,
    curveToNative,
    lineToNative,
    polycurveToNative,
    polylineToNative,
    polylineToSpeckle,
    speckleArcCircleToPoints,
    multiPolylineToSpeckle,
)
from speckle.speckle.converter.geometry.point import (
    pointToCoord,
    pointToNative,
    pointToSpeckle,
    multiPointToSpeckle,
)

from speckle.speckle.converter.layers.utils import findTransformation
from speckle.speckle.utils.panel_logging import logToUser

import numpy as np


def convertToSpeckle(
    feature, index, layer, data, dataStorage
) -> Tuple[Union[Base, Sequence[Base], None], int]:
    """Converts the provided layer feature to Speckle objects"""
    print("___convertToSpeckle____________")
    try:
        iterations = 0
        layer_sr = data.spatialReference  # if sr.type == "Projected":
        geomType = data.shapeType  # Polygon, Point, Polyline, Multipoint, MultiPatch
        featureType = data.featureType
        projectCRS = dataStorage.project.activeMap.spatialReference
        units = dataStorage.currentUnits

        xform_vars = (geomType, layer_sr, projectCRS, layer)
        # f_shape = findTransformation(feature, geomType, layer_sr, projectCRS, layer)
        # if f_shape is None:
        #    return None

        print(feature.isMultipart)  # e.g. False
        print(feature.partCount)
        # geomMultiType = feature.isMultipart
        hasCurves = feature.hasCurves

        # feature is <geoprocessing describe geometry object object at 0x000002A75D6A4BD0>

        # print(featureType) # e.g. Simple
        # print(geomType) # e.g. Polygon
        # geomSingleType = (featureType=="Simple") # Simple,SimpleJunction,SimpleJunction,ComplexEdge,Annotation,CoverageAnnotation,Dimension,RasterCatalogItem

        if geomType == "Point":  # Polygon, Point, Polyline, Multipoint, MultiPatch
            print("__Point conversion")
            f_shape = findTransformation(feature, geomType, layer_sr, projectCRS, layer)
            if f_shape is None:
                return None
            result = [pointToSpeckle(feature.getPart(), feature, layer, dataStorage)]
            for r in result:
                r.units = units

            element = GisPointElement(units=units, geometry=result)

        elif geomType == "Multipoint":
            print("__Multipoint conversion")
            f_shape = findTransformation(feature, geomType, layer_sr, projectCRS, layer)
            if f_shape is None:
                return None
            result = [
                pointToSpeckle(pt, feature, layer, dataStorage)
                for pt in feature.getPart()
            ]
            for r in result:
                r.units = units

            element = GisPointElement(units=units, geometry=result)

        elif geomType == "Polyline":
            print("__Polyline conversion")
            # if feature.partCount == 1:
            #    result = anyLineToSpeckle(
            #        feature, feature, layer, dataStorage, xform_vars
            #    )
            #    result = addCorrectUnits(result, dataStorage)
            #    result = [result]
            # else:
            all_parts = []
            for part in feature.getPart():
                all_parts.append(
                    arcpy.Polyline(
                        part,
                        arcpy.Describe(layer.dataSource).SpatialReference,
                        has_z=True,
                    )
                )
            result = [
                anyLineToSpeckle(poly, feature, layer, dataStorage, xform_vars)
                for poly in all_parts
            ]
            for r in result:
                r = addCorrectUnits(r, dataStorage)

            element = GisLineElement(units=units, geometry=result)

        elif geomType == "Polygon":
            print("__Polygon conversion")
            # if feature.partCount > 1:
            r"""
            if feature.partCount == 1:
                result = polygonToSpeckle(
                    feature, feature, index, layer, dataStorage, xform_vars
                )
                result = [result]

            else:
            """
            result = [
                polygonToSpeckle(geom, feature, index, layer, dataStorage, xform_vars)
                for geom in feature.getPart()
            ]

            for r in result:
                if r is None:
                    continue
                r.units = units
                if r.boundary is not None:
                    r.boundary.units = units
                if r.voids is not None:
                    for v in r.voids:
                        if v is not None:
                            v.units = units
                    for v in r.displayValue:
                        if v is not None:
                            v.units = units
            element = GisPolygonElement(units=units, geometry=result)

        elif geomType == "MultiPatch":
            f_shape = findTransformation(feature, geomType, layer_sr, projectCRS, layer)
            if f_shape is None:
                return None
            result = [polygonToSpeckleMesh(feature, index, layer, False, dataStorage)]
            for r in result:
                if r is None:
                    continue
                r.units = units
                if r.boundary is not None:
                    r.boundary.units = units
                if r.voids is not None:
                    for v in r.voids:
                        if v is not None:
                            v.units = units
                    for v in r.displayValue:
                        if v is not None:
                            v.units = units
            element = GisPolygonElement(units=units, geometry=result)
            print(element)
        else:
            logToUser(
                "Unsupported or invalid geometry in layer " + layer.name,
                level=1,
                func=inspect.stack()[0][3],
            )
        return element, iterations
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None, None


def convertToNative(
    base: Base, sr: arcpy.SpatialReference, dataStorage
) -> Union[Any, None]:
    """Converts any given base object to QgsGeometry."""
    print("___Convert to Native SingleType___")
    converted = None
    try:
        # print(base)
        conversions = [
            (Point, pointToNative),
            (Line, lineToNative),
            (Polyline, polylineToNative),
            (Curve, curveToNative),
            (Arc, arcToNative),
            (Circle, circleToNative),
            (Ellipse, ellipseToNative),
            # (Mesh, meshToNative),
            (Polycurve, polycurveToNative),
            # temporary solution for polygons (Speckle has no type Polygon yet)
        ]

        for conversion in conversions:
            if isinstance(base, conversion[0]):
                # print(conversion[0])
                converted = conversion[1](base, sr, dataStorage)
                break

        if converted is None:
            # distinguish normal QGIS polygons and the ones sent as Mesh only
            try:
                if isinstance(base, GisPolygonGeometry):
                    if base.boundary is None:
                        try:
                            converted = meshToNative(base.displayValue, sr, dataStorage)
                        except KeyError as e:
                            # print(e)
                            converted = meshToNative(
                                base["@displayValue"], sr, dataStorage
                            )
                    else:
                        converted = multiPolygonToNative(base, sr, dataStorage)
                else:
                    # for older commits
                    boundary = base.boundary  # will throw exception if not polygon
                    if boundary is None:
                        try:
                            converted = meshToNative(base.displayValue, sr, dataStorage)
                        except:
                            converted = meshToNative(
                                base["@displayValue"], sr, dataStorage
                            )
                    elif boundary is not None and isinstance(base, conversion[0]):
                        converted = multiPolygonToNative(base, sr, dataStorage)

            except (
                Exception
            ) as e:  # if no "boundary" found (either old Mesh from QGIS or other object)
                print(e)
                try:  # check for a QGIS Mesh
                    try:
                        # if sent as Mesh
                        colors = base.displayValue[0].colors  # will throw exception
                        if isinstance(base.displayValue[0], Mesh):
                            converted = meshToNative(
                                base.displayValue, sr, dataStorage
                            )  # only called for Meshes created in QGIS before
                    except:
                        # if sent as Mesh
                        colors = base["@displayValue"][0].colors  # will throw exception
                        if isinstance(base["@displayValue"][0], Mesh):
                            converted = meshToNative(
                                base["@displayValue"], sr, dataStorage
                            )  # only called for Meshes created in QGIS before

                except:  # any other object(
                    pass
        if converted is None:
            converted = multiPolygonToNative(base, sr, dataStorage)
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return converted


def multiPointToNative(items: List[Point], sr: arcpy.SpatialReference, dataStorage):
    print("___Create MultiPoint")
    features = None
    try:
        all_pts = []
        # example https://pro.arcgis.com/en/pro-app/2.8/arcpy/classes/multipoint.htm
        for item in items:
            pt = pointToCoord(item)  # [x, y, z]
            all_pts.append(arcpy.Point(pt[0], pt[1], pt[2]))
        # print(all_pts)
        features = arcpy.Multipoint(arcpy.Array(all_pts))
        # if len(features)==0: features = None
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return features


def multiPolylineToNative(
    items: List[Polyline], sr: arcpy.SpatialReference, dataStorage
):
    print("_______Drawing Multipolylines____")
    poly = None
    try:
        # print(items)
        poly = None
        full_array_list = []
        for item in items:  # will be 1 item
            pointsSpeckle = []
            try:
                pointsSpeckle = item.as_points()
            except:
                continue
            pts = [pointToCoord(pt) for pt in pointsSpeckle]

            if item.closed is True:
                pts.append(pointToCoord(item.as_points()[0]))

            arr = [arcpy.Point(*coords) for coords in pts]
            full_array_list.append(arr)

        poly = arcpy.Polyline(arcpy.Array(full_array_list), sr, has_z=True)
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return poly


def convertToNativeMulti(items: List[Base], sr: arcpy.SpatialReference, dataStorage):
    print("___Convert to Native MultiType___")
    try:
        first = items[0]
        if isinstance(first, Point):
            return multiPointToNative(items, sr, dataStorage)
        elif isinstance(first, Line) or isinstance(first, Polyline):
            return multiPolylineToNative(items, sr, dataStorage)
        elif isinstance(first, Base):
            try:
                if first["boundary"] is not None and first["voids"] is not None:
                    print(first["boundary"])
                    print(first["voids"])
                    return multiPolygonToNative(items, sr, dataStorage)
            except:
                return None
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None

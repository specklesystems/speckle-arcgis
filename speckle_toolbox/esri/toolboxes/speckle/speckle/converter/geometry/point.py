import math
from typing import List
from specklepy.objects.geometry import Point
import arcpy

import inspect
from speckle.speckle.converter.geometry.utils import (
    transform_speckle_pt_on_receive,
    apply_pt_transform_matrix,
)

from speckle.speckle.converter.layers.utils import get_scale_factor
from speckle.speckle.utils.panel_logging import logToUser


def multiPointToSpeckle(geom, feature, layer, multiType: bool):
    """Converts a Point to Speckle"""

    pointList = []
    # print(geom) # <geoprocessing describe geometry object object at 0x0000020F1D94AB10>
    try:
        if multiType is False:
            for pt in geom:
                # print(pt) # 284394.58100903 5710688.11602606 NaN NaN <class 'arcpy.arcobjects.arcobjects.Point'>
                # print(type(pt))
                if pt != None:
                    pointList.append(pointToSpeckle(pt, feature, layer))
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return pointList


def pointToSpeckle(pt, feature, layer):
    """Converts a Point to Speckle"""
    # print("___Point to Speckle____")
    # when unset, z() returns "nan"
    # print(pt) # 4.9046319 52.3592043 NaN NaN
    # print("____Point to Speckle___")
    try:
        x = pt.X
        y = pt.Y
        if pt.Z:
            z = pt.Z
        else:
            z = 0
        specklePoint = Point(units="m")
        specklePoint.x = x
        specklePoint.y = y
        specklePoint.z = z
        """
        if feature is not None and layer is not None: # can be if it's a point from raster layer 
            col = featureColorfromNativeRenderer(feature, layer)
            specklePoint['displayStyle'] = {}
            specklePoint['displayStyle']['color'] = col
        """
        # print(specklePoint)
        return specklePoint
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None


def pointToNative(
    pt: Point, sr: arcpy.SpatialReference, dataStorage
) -> arcpy.PointGeometry:
    """Converts a Speckle Point to QgsPoint"""
    try:
        new_pt = scalePointToNative(pt, pt.units, dataStorage)
        new_pt = apply_pt_transform_matrix(new_pt, dataStorage)
        newPt = transform_speckle_pt_on_receive(new_pt, dataStorage)

        geom = arcpy.PointGeometry(arcpy.Point(pt.x, pt.y, pt.z), sr, has_z=True)
        # print(geom)
        return geom

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None


def pointToNativeWithoutTransforms(pt: Point, sr: arcpy.SpatialReference, dataStorage):
    """Converts a Speckle Point to QgsPoint"""
    try:
        new_pt = scalePointToNative(pt, pt.units, dataStorage)
        new_pt = apply_pt_transform_matrix(new_pt, dataStorage)

        geom = arcpy.PointGeometry(arcpy.Point(pt.x, pt.y, pt.z), sr, has_z=True)
        # print(geom)
        return geom

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def pointToCoord(point: Point) -> List[float]:
    """Converts a Speckle Point to QgsPoint"""
    try:
        pt = scalePointToNative(point, point.units)
        coords = [pt.x, pt.y, pt.z]
        # print(coords)
        return coords
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return [None, None, None]


def scalePointToNative(point: Point, units: str, dataStorage=None) -> Point:
    """Scale point coordinates to meters"""
    try:
        scaleFactor = get_scale_factor(units)
        pt = Point(units="m")
        pt.x = point.x * scaleFactor
        pt.y = point.y * scaleFactor
        pt.z = 0 if math.isnan(point.z) else point.z * scaleFactor
        return pt
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None


def addZtoPoint(coords: List):
    try:
        if len(coords) == 2:
            coords.append(0)
        return coords
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None

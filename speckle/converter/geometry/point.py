import math
from typing import List
from specklepy.objects.geometry import Point
import arcpy

from speckle.converter.layers.utils import get_scale_factor

def pointToSpeckle(pt, feature, layer):
  
    """Converts a QgsPoint to Speckle"""
    # when unset, z() returns "nan"
    #print(pt) # 4.9046319 52.3592043 NaN NaN
    x = pt.X
    y = pt.Y
    if pt.Z: z = pt.Z 
    else: z = 0
    specklePoint = Point(units = "m")
    specklePoint.x = x
    specklePoint.y = y
    specklePoint.z = z
    '''
    col = featureColorfromNativeRenderer(feature, layer)
    specklePoint['displayStyle'] = {}
    specklePoint['displayStyle']['color'] = col
    '''
    return specklePoint

def pointToNative(pt: Point, sr: arcpy.SpatialReference) -> arcpy.PointGeometry:
    """Converts a Speckle Point to QgsPoint"""
    pt = scalePointToNative(pt, pt.units)
    geom = arcpy.PointGeometry(arcpy.Point(pt.x, pt.y), sr)
    return geom

def pointToCoord(pt: Point) -> List[float]:
    """Converts a Speckle Point to QgsPoint"""
    pt = scalePointToNative(pt, pt.units)
    return [pt.x, pt.y, pt.z]

def scalePointToNative(pt: Point, units: str) -> Point:
    """Scale point coordinates to meters"""
    scaleFactor = get_scale_factor(units)
    pt.x = pt.x * scaleFactor
    pt.y = pt.y * scaleFactor
    pt.z = 0 if math.isnan(pt.z) else pt.z * scaleFactor
    return pt

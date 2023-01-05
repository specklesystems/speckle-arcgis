import math
from typing import List
from specklepy.objects.geometry import Point
import arcpy

try: from speckle.converter.layers.utils import get_scale_factor
except: from speckle_toolbox.esri.toolboxes.speckle.converter.layers.utils import get_scale_factor


def multiPointToSpeckle(geom, feature, layer, multiType: bool):
    """Converts a Point to Speckle"""
    #try: 
    #print("___Point to Speckle____")
    #point = Point(units = "m")
    pointList = []
    #print(geom) # <geoprocessing describe geometry object object at 0x0000020F1D94AB10>
    #print(multiType)

    if multiType is False: 
        for pt in geom:
            #print(pt) # 284394.58100903 5710688.11602606 NaN NaN <class 'arcpy.arcobjects.arcobjects.Point'> 
            #print(type(pt))
            if pt != None: pointList.append(pointToSpeckle(pt, feature, layer)) 
    return pointList

def pointToSpeckle(pt, feature, layer):
  
    """Converts a Point to Speckle"""
    #print("___Point to Speckle____")
    # when unset, z() returns "nan"
    #print(pt) # 4.9046319 52.3592043 NaN NaN
    #print("____Point to Speckle___")
    x = pt.X
    y = pt.Y
    if pt.Z: z = pt.Z 
    else: z = 0
    specklePoint = Point(units = "m")
    specklePoint.x = x
    specklePoint.y = y
    specklePoint.z = z
    '''
    if feature is not None and layer is not None: # can be if it's a point from raster layer 
        col = featureColorfromNativeRenderer(feature, layer)
        specklePoint['displayStyle'] = {}
        specklePoint['displayStyle']['color'] = col
    '''
    #print(specklePoint)
    return specklePoint

def pointToNative(pt: Point, sr: arcpy.SpatialReference) -> arcpy.PointGeometry:
    """Converts a Speckle Point to QgsPoint"""
    #print("___pointToNative__")
    #print(pt)
    pt = scalePointToNative(pt, pt.units)
    geom = arcpy.PointGeometry(arcpy.Point(pt.x, pt.y, pt.z), sr, has_z = True)
    #print(geom)
    return geom

def pointToCoord(point: Point) -> List[float]:
    """Converts a Speckle Point to QgsPoint"""
    pt = scalePointToNative(point, point.units)
    coords = [pt.x, pt.y, pt.z]
    #print(coords)
    return coords

def scalePointToNative(point: Point, units: str) -> Point:
    """Scale point coordinates to meters"""
    scaleFactor = get_scale_factor(units)
    pt = Point(units = "m")
    pt.x = point.x * scaleFactor
    pt.y = point.y * scaleFactor
    pt.z = 0 if math.isnan(point.z) else point.z * scaleFactor
    return pt

def addZtoPoint(coords: List): 
    if len(coords) == 2: coords.append(0)
    return coords
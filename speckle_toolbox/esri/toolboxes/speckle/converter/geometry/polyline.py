
from math import atan, cos, sin
import math
from typing import List, Union
from specklepy.objects.geometry import Point, Line, Polyline, Curve, Arc, Circle, Polycurve, Plane, Interval  
import arcpy 

from speckle.converter.geometry.point import pointToCoord, pointToNative, pointToSpeckle
from speckle.converter.layers.utils import get_scale_factor

def circleToSpeckle(center, point, layer):
    print("___Circle to Speckle____")
    rad = math.sqrt(math.pow((center[0] - point[0]),2) + math.pow((center[1] - point[1]),2) )
    print(rad)
    if len(center)>2: center_z = center[2]
    else: center_z = 0
    length = rad*2*math.pi
    domain = [0, length] 
    plane = [center[0], center[1], center_z, 0,0,1, 1,0,0, 0,1,0] 
    units = 3 #"m" 

    args = [0] + [rad] + domain + plane + [units] 
    print(args) 
    c = Circle().from_list(args)
    #c.length = length
    #c.domain = Interval.from_list([0, 1])
    print(c)
    return c 

def polylineToSpeckle(geom, feature, layer, multiType: bool):
    #try: 
    print("___Polyline to Speckle____")
    polyline = None
    pointList = []
    print(geom.hasCurves) 
    #print(geom) # <geoprocessing describe geometry object object at 0x0000020F1D94AB10>
    #print(multiType)

    if multiType is False: 
        for p in geom: 
            #print(p) # <geoprocessing array object object at 0x0000020F1D972C90>
            for pt in p: 
                #print(pt) # 284394.58100903 5710688.11602606 NaN NaN 
                #print(type(pt)) #<class 'arcpy.arcobjects.arcobjects.Point'> 
                if pt != None: pointList.append(pt) 
        closed = False
        if pointList[0] == pointList[len(pointList)-1]: 
            closed = True
            pointList = pointList[:-1]
        polyline = polylineFromVerticesToSpeckle(pointList, closed, feature, layer) 

    return polyline

def polylineFromVerticesToSpeckle(vertices, closed, feature, layer):
    """Converts a Polyline to Speckle"""
    
    print("___PolyLINE to Speckle____")
    specklePts = []
    for pt in vertices:
        newPt = pointToSpeckle(pt, feature, layer) 
        specklePts.append(newPt)
    print(len(specklePts))
    print(specklePts)

    # TODO: Replace with `from_points` function when fix is pushed.
    polyline = Polyline(units = "m")
    polyline.value = []
    polyline.closed = closed
    polyline.units = specklePts[0].units
    for i, point in enumerate(specklePts):
        if closed and i == len(specklePts) - 1:
            continue
        polyline.value.extend([point.x, point.y, point.z])
    print(polyline)
    '''
    col = featureColorfromNativeRenderer(feature, layer)
    polyline['displayStyle'] = {}
    polyline['displayStyle']['color'] = col
    '''
    return polyline


def polylineToNative(poly: Polyline, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Polyline to QgsLineString"""
    print("__ convert poly to native __")
    print(poly)
    pts = [pointToCoord(pt) for pt in poly.as_points()]
    if poly.closed is True: 
        pts.append( pointToCoord(poly.as_points()[0]) )
    #print(pts)
    polyline = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in pts]), sr )
    #print(polyline)
    return polyline


def lineToNative(line: Line, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Line to QgsLineString"""
    pts = [pointToCoord(pt) for pt in [line.start, line.end]]
    line = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in pts]), sr )
    return line

def curveToNative(poly: Curve, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Curve to QgsLineString"""
    display = poly.displayValue
    curve = polylineToNative(display, sr) 
    return curve

def arcToNative(poly: Arc, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Arc to QgsCircularString"""
    arc = arcToNativePoints(poly, sr) #QgsCircularString(pointToNative(poly.startPoint), pointToNative(poly.midPoint), pointToNative(poly.endPoint))
    return arc

def circleToNative(poly: Circle, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Circle to QgsLineString"""
    scaleFactor = get_scale_factor(poly.units)
    circ = None #QgsCircle(pointToNative(poly.plane.origin), poly.radius * scaleFactor)
    #circ = circ.toLineString() # QgsCircle is not supported to be added as a feature 
    return circ

def polycurveToNative(poly: Polycurve, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    points = []
    curve = None
    r'''
    try:
        for segm in poly.segments: # Line, Polyline, Curve, Arc, Circle
            if isinstance(segm,Line):  converted = lineToNative(segm) # QgsLineString
            elif isinstance(segm,Polyline):  converted = polylineToNative(segm) # QgsLineString
            elif isinstance(segm,Curve):  converted = curveToNative(segm) # QgsLineString
            elif isinstance(segm,Circle):  converted = circleToNative(segm) # QgsLineString
            elif isinstance(segm,Arc):  converted = arcToQgisPoints(segm) # QgsLineString
            else: # either return a part of the curve, of skip this segment and try next
                arcpy.AddWarning(f"Part of the polycurve cannot be converted")
                curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]) )
                return curve
            if converted is not None: 
                for pt in converted.getPart({0}):
                    if len(points)>0 and pt.X == points[len(points)-1].X and pt.Y== points[len(points)-1].Y and pt.Z== points[len(points)-1].Z: pass
                    else: points.append([pt.X, pt.Y, pt.Z])
            else:
                arcpy.AddWarning(f"Part of the polycurve cannot be converted")
                curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]) )
                return curve
    except: curve = None
    '''
    #curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]), sr )
    return curve

def arcToNativePoints(poly: Arc, sr: arcpy.SpatialReference):
    points = []
    if poly.startPoint.x == poly.plane.origin.x: angle1 = math.pi/2
    else: angle1 = atan( abs ((poly.startPoint.y - poly.plane.origin.y) / (poly.startPoint.x - poly.plane.origin.x) )) # between 0 and pi/2

    if poly.plane.origin.x < poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = 2*math.pi - angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = math.pi + angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y < poly.startPoint.y: angle1 = math.pi - angle1

    try: 
        pointsNum = math.floor( abs(poly.endAngle - poly.startAngle)) * 12
        if pointsNum <4: pointsNum = 4
        points.append(pointToCoord(poly.startPoint))

        for i in range(1, pointsNum + 1): 
            k = i/pointsNum # to reset values from 1/10 to 1
            angle = angle1 + k * ( poly.endAngle - poly.startAngle) * poly.plane.normal.z
            pt = Point( x = poly.plane.origin.x + poly.radius * cos(angle), y = poly.plane.origin.y + poly.radius * sin(angle), z = 0) 
            pt.units = poly.startPoint.units 
            points.append(pointToCoord(pt))
        points.append(pointToCoord(poly.endPoint))
        curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]), sr )
        return curve
    except: return None

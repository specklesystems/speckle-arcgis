
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
    #print(rad)
    if len(center)>2: center_z = center[2]
    else: center_z = 0
    length = rad*2*math.pi
    domain = [0, length] 
    plane = [center[0], center[1], center_z, 0,0,1, 1,0,0, 0,1,0] 
    units = 3 #"m" 

    args = [0] + [rad] + domain + plane + [units] 
    #print(args) 
    c = Circle().from_list(args)
    #print(c)
    return c 

def polylineToSpeckle(geom, feature, layer, multiType: bool):
    print("___Polyline to Speckle____")
    polyline = None
    pointList = []
    #print(geom.hasCurves) 

    if multiType is False: 
        for p in geom: 
            for pt in p: 
                if pt != None: pointList.append(pt)#; print(pt.Z)
        closed = False
        if pointList[0] == pointList[len(pointList)-1]: 
            closed = True
            pointList = pointList[:-1]
        polyline = polylineFromVerticesToSpeckle(pointList, closed, feature, layer) 

    return polyline

def polylineFromVerticesToSpeckle(vertices, closed, feature, layer):
    """Converts a Polyline to Speckle"""
    
    print("___Polyline from vertices to Speckle____")
    specklePts = []
    for pt in vertices:
        newPt = pointToSpeckle(pt, feature, layer) 
        specklePts.append(newPt)

    # TODO: Replace with `from_points` function when fix is pushed.
    polyline = Polyline(units = "m")
    polyline.value = []
    polyline.closed = closed
    polyline.units = specklePts[0].units
    for i, point in enumerate(specklePts):
        if closed and i == len(specklePts) - 1:
            continue
        polyline.value.extend([point.x, point.y, point.z])

    return polyline


def polylineToNative(poly: Polyline, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Polyline to QgsLineString"""
    print("__ convert poly to native __")
    pts = [pointToCoord(pt) for pt in poly.as_points()]
    if poly.closed is True: 
        pts.append( pointToCoord(poly.as_points()[0]) )

    pts_coord_list = [arcpy.Point(*coords) for coords in pts]
    polyline = arcpy.Polyline( arcpy.Array(pts_coord_list), sr, has_z=True )
    #print(polyline.JSON)
    return polyline


def lineToNative(line: Line, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Line to QgsLineString"""
    print("___Line to Native___")
    pts = [pointToCoord(pt) for pt in [line.start, line.end]]
    line = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in pts]), sr , has_z=True)
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
    print("___Convert Circle from Native___")
    points = []
    angle1 = math.pi/2
    
    pointsNum = math.floor(math.pi*2) * 12 
    if pointsNum <4: pointsNum = 4
    points.append(pointToCoord(poly.plane.origin))

    radScaled = poly.radius * get_scale_factor(poly.units)
    points[0][1] += radScaled

    for i in range(1, pointsNum + 1): 
        k = i/pointsNum # to reset values from 1/10 to 1
        if poly.plane.normal.z == 0: normal = 1
        else: normal = poly.plane.normal.z
        angle = angle1 + k * math.pi*2 * normal
        pt = Point( x = poly.plane.origin.x + radScaled * cos(angle), y = poly.plane.origin.y + radScaled * sin(angle), z = 0) 
        pt.units = "m"
        points.append(pointToCoord(pt))
    points.append(points[0])
    curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]), sr , has_z=True)
    return curve

def polycurveToNative(poly: Polycurve, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    points = []
    curve = None
    print("___Polycurve to native___")
    
    try:
        for segm in poly.segments: # Line, Polyline, Curve, Arc, Circle
            #print(segm)
            if isinstance(segm,Line):  converted = lineToNative(segm, sr) # QgsLineString
            elif isinstance(segm,Polyline):  converted = polylineToNative(segm, sr) # QgsLineString
            elif isinstance(segm,Curve):  converted = curveToNative(segm, sr) # QgsLineString
            elif isinstance(segm,Circle):  converted = circleToNative(segm, sr) # QgsLineString
            elif isinstance(segm,Arc):  converted = arcToNativePoints(segm, sr) # QgsLineString
            else: # either return a part of the curve, of skip this segment and try next
                arcpy.AddWarning(f"Part of the polycurve cannot be converted")
                curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]), sr , has_z=True)
                return curve
            if converted is not None: 
                #print(converted) # <geoprocessing describe geometry object object at 0x000002B2D3E338D0>
                for part in converted:
                    #print(part) # <geoprocessing array object object at 0x000002B2D2E09530>
                    for pt in part: 
                        #print(pt) # 64.4584221540162 5.5 NaN NaN
                        if pt.Z != None: pt_z = pt.Z
                        else: pt_z = 0
                        #print(pt_z)
                        #print(len(points)) 
                        if len(points)>0 and pt.X == points[len(points)-1][0] and pt.Y == points[len(points)-1][1] and pt_z == points[len(points)-1][2]: pass
                        else: points.append(pointToCoord(Point(x=pt.X, y = pt.Y, z = pt_z)))
                        #print(points)
            else:
                arcpy.AddWarning(f"Part of the polycurve cannot be converted")
                curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]), sr, has_z=True )
                return curve
    except: curve = None
    #print(curve)
    
    curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]), sr, has_z=True )
    return curve

def arcToNativePoints(poly: Arc, sr: arcpy.SpatialReference):
    print("__Arc to native__")
    points = []
    if poly.startPoint.x == poly.plane.origin.x: angle1 = math.pi/2
    else: angle1 = atan( abs ((poly.startPoint.y - poly.plane.origin.y) / (poly.startPoint.x - poly.plane.origin.x) )) # between 0 and pi/2
    
    if poly.plane.origin.x < poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = 2*math.pi - angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = math.pi + angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y < poly.startPoint.y: angle1 = math.pi - angle1
    #print(angle1)
    if poly.endPoint.x == poly.plane.origin.x: angle2 = math.pi/2
    else: angle2 = atan( abs ((poly.endPoint.y - poly.plane.origin.y) / (poly.endPoint.x - poly.plane.origin.x) )) # between 0 and pi/2

    if poly.plane.origin.x < poly.endPoint.x and poly.plane.origin.y > poly.endPoint.y: angle2 = 2*math.pi - angle2
    if poly.plane.origin.x > poly.endPoint.x and poly.plane.origin.y > poly.endPoint.y: angle2 = math.pi + angle2
    if poly.plane.origin.x > poly.endPoint.x and poly.plane.origin.y < poly.endPoint.y: angle2 = math.pi - angle2
    #print(angle2)

    #print(poly.endAngle)
    #print(poly.startAngle)

    try: interval = (poly.endAngle - poly.startAngle); print(interval)
    except: interval = (angle2-angle1); print("recalculate"); print(interval)
    pointsNum = math.floor( abs(interval)) * 12
    if pointsNum <4: pointsNum = 4
    points.append(pointToCoord(poly.startPoint))
    #print(points)
    #print(interval)
    #print(pointsNum)
    for i in range(1, pointsNum + 1): 
        k = i/pointsNum # to reset values from 1/10 to 1
        if poly.plane.normal.z == 0: normal = 1
        else: normal = poly.plane.normal.z
        angle = angle1 + k * interval * normal

        #print(f"k: {str(i)} multiplied: {str(k*interval)} angle: {str(angle1 + k * interval)}")
        #print(cos(angle))
        pt = Point( x = poly.plane.origin.x + poly.radius * cos(angle), y = poly.plane.origin.y + poly.radius * sin(angle), z = 0) 
        pt.units = poly.startPoint.units 
        points.append(pointToCoord(pt))
        #print(pointToCoord(pt))
    points.append(pointToCoord(poly.endPoint))
    #print(points)
    curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]), sr, has_z=True )
    return curve


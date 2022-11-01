
from math import atan, cos, sin
import math
import json 
from typing import List, Union, Tuple
from specklepy.objects import Base 
from specklepy.objects.geometry import Box, Vector, Point, Line, Polyline, Curve, Ellipse, Arc, Circle, Polycurve, Plane, Interval  
import arcpy 
import numpy as np

from speckle.converter.geometry.point import pointToCoord, pointToSpeckle, addZtoPoint
from speckle.converter.layers.utils import get_scale_factor

def circleToSpeckle(center, point):
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
    c = Circle.from_list(args)
    c.plane.origin.units = "m"
    c.units = "m"
    #print(c)
    return c 

def multiPolylineToSpeckle(geom, feature, layer, multiType: bool):

    print("___MultiPolyline to Speckle____")
    polyline = []
    print(enumerate(geom.getPart()))
    for i,x in enumerate(geom.getPart()):
        poly = arcpy.Polyline(x, arcpy.Describe(layer.dataSource).SpatialReference, has_z = True)
        print(poly)
        polyline.append(polylineToSpeckle(poly, feature, layer, poly.isMultipart))

    return polyline

def polylineToSpeckle(geom, feature, layer, multiType: bool):
    print("___Polyline to Speckle____")
    polyline = None
    pointList = []
    print(geom.hasCurves) 

    if multiType is False: 
        if geom.hasCurves: 
            print("has curves")
            # geometry SHAPE@ tokens: https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/reading-geometries.htm
            print(geom.JSON) 
            polyline = curveToSpeckle(geom, "Polyline", feature, layer)
        else:
            for p in geom: 
                for pt in p: 
                    if pt != None: pointList.append(pt)#; print(pt.Z)
            closed = False
            if pointList[0] == pointList[len(pointList)-1]: 
                closed = True
                pointList = pointList[:-1]
            polyline = polylineFromVerticesToSpeckle(pointList, closed, feature, layer) 
    return polyline

def polylineFromVerticesToSpeckle(vertices: List[Point], closed: bool, feature, layer) -> Polyline:
    """Converts a Polyline to Speckle"""
    
    print("___Polyline from vertices to Speckle____")
    
    if isinstance(vertices, list): 
        if len(vertices) > 0 and isinstance(vertices[0], Point):
            specklePts = vertices
        else: specklePts = [pointToSpeckle(pt, feature, layer) for pt in vertices] #breaks unexplainably
    #elif isinstance(vertices, QgsVertexIterator):
    #    specklePts = [pointToSpeckle(pt, feature, layer) for pt in vertices]
    else: return None

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
        if closed and i == len(specklePts) - 1 and specklePts[0] == point: 
            continue # if we consider the last pt, do not add is coincides with the first (and type is Closed) 
        polyline.value.extend([point.x, point.y, point.z])

    return polyline

def arc3ptToSpeckle(p0: List, p1: List, p2: List, feature, layer) -> Arc: 
    print("____arc 3pt to Speckle___")
    p0 = addZtoPoint(p0)
    p1 = addZtoPoint(p1)
    p2 = addZtoPoint(p2)
    arc = Arc()
    arc.startPoint = pointToSpeckle(arcpy.Point(*p0), feature, layer)
    arc.midPoint = pointToSpeckle(arcpy.Point(*p1), feature, layer)
    arc.endPoint = pointToSpeckle(arcpy.Point(*p2), feature, layer)
    center, radius = getArcCenter(Point.from_list(p0), Point.from_list(p1), Point.from_list(p2))
    arc.plane = Plane() #.from_list(Point(), Vector(Point(0, 0, 1)), Vector(Point(0,1,0)), Vector(Point(-1,0,0)))
    arc.plane.origin = Point.from_list(center)
    arc.plane.origin.units = "m" 
    arc.units = "m"
    arc.angleRadians, startAngle, endAngle = getArcRadianAngle(arc)

    arc.radius = radius
    
    arc.plane.normal = getArcNormal(arc, arc.midPoint)

    #arc.angleRadians = abs(angle1 + angle2)
    #print(arc.angleRadians)

    #col = featureColorfromNativeRenderer(feature, layer)
    #arc['displayStyle'] = {}
    #arc['displayStyle']['color'] = col

    return arc

def curveBezierToSpeckle(segmStartCoord, segmEndCoord, knots, feature, layer): 
    print("____bezier curve to Speckle____")
    degree = 3
    points = [
        tuple(knots[0]), tuple(segmStartCoord), tuple(knots[1]), tuple(segmEndCoord)
    ] #[segmStartCoord, *coords]
    print(points)
    num_points = len(points) #2

    knot_count = num_points + degree - 1 #4
    knots = [0] * knot_count
    print(knots)
    for i in range(1, len(knots)):
        knots[i] = i // 3
        print(knots[i])

    length = 1 #spline.calc_length()
    domain = Interval(start=0, end=length, totalChildrenCount=0)
    points = [tuple(pt) for pt in points]
    curve = Curve(
        degree = degree,
        closed = False, 
        periodic= True if (segmStartCoord == segmEndCoord) else False,
        points= list(sum(points, ())),  # magic (flatten list of tuples)
        weights=[1] * num_points,
        knots=knots,
        rational=False,
        area=0,
        volume=0,
        length=length,
        domain=domain,
        units="m",
        bbox=Box(area=0.0, volume=0.0),
    )
    print(curve) 
    return curve


def curveToSpeckle(geom, geomType, feature, layer) -> Union[Circle, Arc, Polyline, Polycurve]:
    print("____curve to Speckle____")
    print(geomType)
    # look for "curvePaths" or "curveRings"[[ (startPt, {arcs, beziers etc}, optional(endPt))],[],...], "rings" 
    # examples: https://developers.arcgis.com/documentation/common-data-types/geometry-objects.htm
    # e.g. {"hasZ":true,
    # "curveRings":[[[631307.05960000027,5803698.4477999993,0],{"a":[[631307.05960000027,5803698.4477999993,0],[631307.05960000027,5803414.92656173],0,1]}]],
    # "spatialReference":{"wkid":32631,"latestWkid":32631}}
    
    # b - bezier curve (endPt, controlPts) 
    # a - elliptical arc (endPt, centralPt) e.g. for circle: [[[631307.05960000027,5803698.4477999993,0],{"a":[[631307.05960000027,5803698.4477999993,0],[631307.05960000027,5803414.92656173],0,1]}]]
    # c - circular arc (endPt, throughPt) e.g. [[[633242.45179999992,5803058.0354999993,0],{"c":[[633718.26040000003,5803496.4210000001,0],[633337.75764975848,5803431.9997026781]]},[633242.45179999992,5803058.0354999993,0]]]
    
    boundary = Polycurve(units = "m")
    if geomType == "Polyline": boundary.closed = False
    else: boundary.closed = True 
    segments = [] 

    for key, val in json.loads(geom.JSON).items(): 
        print(key)
        if key == "curveRings" or key == "curvePaths": 
            
            #boundary.closed = True
            includesLines = 0

            for segm in val: # segm: List
                print(segm) #e.g. [[631307.05960000027,5803698.4477999993,0], {"a":[[631307.05960000027,5803698.4477999993,0],[631307.05960000027,5803414.92656173],0,1]}] 
                segmStartCoord: List = addZtoPoint(segm[0])
                
                # go through all elements (points, a, c, ...)
                for k in range(1, len(segm)):
                    # e.g. one from the list: "curveRings":[[[631750.87200000044,5803159.6126000006,0],
                    # {"c":[[632429.8348000003,5803507.1132999994,0],[631988.22772700491,5803532.9008129537]]},
                    # {"c":[[632590.21970000025,5803127.5355999991,0],[633018.51899157302,5803532.1801161235]]},
                    # [631750.87200000044,5803159.6126000006,0]]]

                    # if previous segments exist 
                    if len(segments) > 0:  
                            segmOldData = segm[k-1] 
                            if isinstance(segmOldData, dict):  # get "end point" of previous segment 
                                for key3, val3 in segmOldData.items(): 
                                    segmStartCoord: List = addZtoPoint(val2[0]) 
                            elif isinstance(segmOldData, list) and isinstance(segmOldData[0], float): 
                                  segmStartCoord: List = segmOldData 
                    segmStartCoord = addZtoPoint(segmStartCoord)

                    if isinstance(segm[k], dict): 
                        for key2, val2 in segm[k].items():
                            if key2 == "a": # elliptical arc (endPt, centralPt)
                                # e.g. {'a': [[633883.1035000002, 5802972.5812, 0], [634028.3379278888, 5802908.342895357], 0, 1, 1.1543577096027686, 473.59966687227444, 0.33531864204900685]}
                                segmEndCoord = addZtoPoint(val2[0]) # [631307.05960000027,5803698.4477999993,0]
                                segmCenter = addZtoPoint(val2[1]) # [631307.05960000027,5803414.92656173]
                                
                                if segmStartCoord == segmEndCoord: 
                                    if len(val2) == 4: 
                                        print("full circle") 
                                        #boundary.closed = True 
                                        segmentLocal = circleToSpeckle(segmCenter, segmEndCoord)
                                        segments.append(segmentLocal)
                                        lastPt = segmEndCoord 
                                        print("segmentLocal:")
                                        print(segmentLocal)
                                        print(segmStartCoord)
                                        print(segmEndCoord)
                                    else: # ellipse
                                        arcpy.AddMessage("SpeckleWarning: ellipse geometry not supported yet") 
                                        segments = []
                                        break
                                else: # elliptical curve
                                    arcpy.AddMessage("SpeckleWarning: ellipse geometry not supported yet") 
                                    segments = []
                                    break

                            if key2 == "c": # circular arc (endPt, throughPt) 
                                
                                segmEndCoord: List = addZtoPoint(val2[0]) # [633718.26040000003,5803496.4210000001,0] 
                                segmThrough: List = addZtoPoint(val2[1]) # [633337.7576497585, 5803431.999702678] 

                                segmentLocal = arc3ptToSpeckle(segmStartCoord, segmThrough, segmEndCoord, feature, layer) 
                                segments.append(segmentLocal)
                                print("segmentLocal:")
                                print(segmentLocal)
                                print(segmStartCoord)
                                print(segmEndCoord)
                                lastPt = segmEndCoord 

                            if key2 == "b": # bezier curve (endPt, controlPts) 
                                arcpy.AddMessage("SpeckleWarning: bezier curve geometry not supported yet") 
                                segments = []
                                break
                                r'''
                                segmEndCoord: List = addZtoPoint(val2[0])  # [633718.26040000003,5803496.4210000001,0] 
                                #segmThrough: List = val2[1] # [633337.7576497585, 5803431.999702678] 
                                coords = val2[1:]
                                segmentLocal = curveBezierToSpeckle(segmStartCoord, segmEndCoord, coords, feature, layer) 
                                segments.append(segmentLocal)
                                print("segmentLocal:")
                                print(segmentLocal)
                                print(segmStartCoord)
                                print(segmEndCoord)
                                
                                lastPt = segmEndCoord 
                                '''
                    
                    elif isinstance(segm[k], list) and isinstance(segm[k][0], float): # add line to point 
                        print("add line")
                        segm[k] = addZtoPoint(segm[k]) 
                        segmentLocal = lineFrom2pt(segmStartCoord, segm[k])
                        includesLines = 1
                        segments.append(segmentLocal) 
                        lastPt = segm[k]

                        print("segmentLocal:")
                        print(segmentLocal)
                        print(segmentLocal.start)
                        print(segmentLocal.end)

                    # for the last point
                    if k == len(segm)-1 and isinstance(segm[k], list): 
                        print("last element is a point (adding line)")
                        lastPt = addZtoPoint(lastPt)
                        if lastPt != segm[0]: 
                            #segmentLocal = lineFrom2pt(lastPt, segm[0])
                            #segments.append(segmentLocal) 
                            #includesLines = 1
                            #print("segmentLocal:")
                            #print(segmentLocal)
                            #print(segmentLocal.start)
                            #print(segmentLocal.end)
                            boundary.closed = True 
                    #pts = speckleArcCircleToPoints(segmentLocal)
                    #pts.append(segm[k])
                    #arcgisPts = [arcpy.Point(pt[0], pt[1], pt[2]) for pt in pts]
                    #segmentLocal = polylineFromVerticesToSpeckle(arcgisPts, True, feature, layer)
    
    boundary.segments = segments
    print(segments)

    if len(segments) == 1:
        boundary = segments[0]
        #if isinstance(boundary, Arc) or isinstance(boundary, Circle): 
        #    boundary.displayValue = Polyline.from_points(speckleArcCircleToPoints(boundary)) 
        
    elif len(segments) > 1: # and includesLines == 0:
        #boundary.displayValue = Polyline.from_points(specklePolycurveToPoints(boundary)) 
        pass
        #boundary.closed = True 
    #elif len(segments) > 1 and includesLines == 1: 
    #    print("includes lines!")
    #    points = specklePolycurveToPoints(boundary) 
    #    boundary = Polyline.from_points(points)
    else: return None

    #boundary.displayValue = Polyline.from_points(specklePolycurveToPoints(boundary)) 
    
    print(boundary)  
    return boundary 



def lineFrom2pt(pt1: List[float], pt2: List[float]): 
    pt1 = addZtoPoint(pt1)
    pt2 = addZtoPoint(pt2)
    dist = math.sqrt( math.pow((pt2[0] - pt1[0]), 2) + math.pow((pt2[1] - pt1[1]), 2) + math.pow((pt2[2] - pt1[2]), 2) ) 
    print(dist) 
    domain = [0, dist, 0, 0] 
    line = Line(units = "m" )#.from_list([*pt1, *pt2, *domain]) 
    line.start = Point.from_list(pt1)
    line.end = Point.from_list(pt2)
    line.start.units = line.end.units = "m" 
    return line 

def polylineToNative(poly: Polyline, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Polyline to QgsLineString"""
    print("__ convert poly to native __")

    if isinstance(poly, Polycurve): 
        poly = specklePolycurveToPoints(poly)
    if isinstance(poly, Arc) or isinstance(poly, Circle): 
        try: poly = poly["displayValue"]
        except: poly = speckleArcCircleToPoints(poly)
        
    if isinstance(poly, list): pts = [pointToCoord(pt) for pt in poly]
    else: pts = [pointToCoord(pt) for pt in poly.as_points()]

    if poly.closed is True: 
        pts.append( pointToCoord(poly.as_points()[0]) )

    pts_coord_list = [arcpy.Point(*coords) for coords in pts]
    polyline = arcpy.Polyline( arcpy.Array(pts_coord_list), sr, has_z=True )
    #print(polyline.JSON)
    return polyline


def lineToNative(line: Line, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Line to Native"""
    print("___Line to Native___")
    pts = [pointToCoord(pt) for pt in [line.start, line.end]]
    line = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in pts]), sr , has_z=True)
    return line

def curveToNative(poly: Curve, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Curve to Native"""
    display = poly.displayValue
    curve = polylineToNative(display, sr) 
    return curve

def arcToNative(poly: Arc, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Arc to Native"""
    arc = arcToNativePolyline(poly, sr) #QgsCircularString(pointToNative(poly.startPoint), pointToNative(poly.midPoint), pointToNative(poly.endPoint))
    return arc

def ellipseToNative():
    return

def circleToNative(poly: Circle, sr: arcpy.SpatialReference) -> arcpy.Polyline:
    """Converts a Speckle Circle to QgsLineString"""
    print("___Convert Circle to Native___")
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
        pt = Point( x = poly.plane.origin.x * get_scale_factor(poly.units) + radScaled * cos(angle), y = poly.plane.origin.y * get_scale_factor(poly.units) + radScaled * sin(angle), z = 0) 
        print(pt)
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
        for i, segm in enumerate(poly.segments): # Line, Polyline, Curve, Arc, Circle
            print("___start segment")            
            if isinstance(segm,Line):  converted = lineToNative(segm, sr) # QgsLineString
            elif isinstance(segm,Polyline):  converted = polylineToNative(segm, sr) # QgsLineString
            elif isinstance(segm,Curve):  converted = curveToNative(segm, sr) # QgsLineString
            elif isinstance(segm,Circle):  converted = circleToNative(segm, sr) # QgsLineString
            elif isinstance(segm,Arc):  converted = arcToNativePolyline(segm, sr) # QgsLineString
            else: # either return a part of the curve, of skip this segment and try next
                arcpy.AddWarning(f"Part of the polycurve cannot be converted")
                curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]), sr , has_z=True)
                return curve
            if converted is not None: 
                #print(converted) # <geoprocessing describe geometry object object at 0x000002B2D3E338D0>
                for part in converted:
                    #print("Part: ")
                    #print(part) # <geoprocessing array object object at 0x000002B2D2E09530>
                    for pt in part: 
                        #print(pt) # 64.4584221540162 5.5 NaN NaN
                        if pt.Z != None: pt_z = pt.Z
                        else: pt_z = 0
                        #print(pt_z)
                        #print(len(points)) 
                        if len(points)>0 and pt.X == points[len(points)-1][0] and pt.Y == points[len(points)-1][1] and pt_z == points[len(points)-1][2]: pass
                        else: points.append(pointToCoord(Point(x=pt.X, y = pt.Y, z = pt_z, units = "m"))) # e.g. [[64.4584221540162, 5.499999999999999, 0.0], [64.45461685210796, 5.587155742747657, 0.0]]
            else:
                arcpy.AddWarning(f"Part of the polycurve cannot be converted")
                curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]), sr, has_z=True )
                return curve
    except: curve = None
    #print(curve)
    
    curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]), sr, has_z=True )
    return curve

def arcToNativePolyline(poly: Union[Arc, Circle], sr: arcpy.SpatialReference):
    print("__Arc/Circle to native polyline__")
    pointsSpeckle = speckleArcCircleToPoints(poly)
    points = [pointToCoord(p) for p in pointsSpeckle]
    curve = arcpy.Polyline( arcpy.Array([arcpy.Point(*coords) for coords in points]), sr, has_z=True )
    return curve



def specklePolycurveToPoints(poly: Polycurve) -> List[Point]:
    print("_____Speckle Polycurve to points____")
    points = []
    for segm in poly.segments:
        print(segm)
        pts = []
        if isinstance(segm, Arc) or isinstance(segm, Circle): # or isinstance(segm, Curve):
            print("Arc or Curve")
            pts: List[Point] = speckleArcCircleToPoints(segm) 
        elif isinstance(segm, Line): 
            print("Line")
            pts: List[Point] = [segm.start, segm.end]
        elif isinstance(segm, Polyline): 
            print("Polyline")
            pts: List[Point] = segm.as_points()

        points.extend(pts)
    return points

def speckleArcCircleToPoints(poly: Union[Arc, Circle]) -> List[Point]: 
    print("__Arc or Circle to Points___")
    points = []
    #print(poly.plane) 
    #print(poly.plane.normal) 
    if poly.plane is None or poly.plane.normal.z == 0: normal = 1 
    else: normal = poly.plane.normal.z 
    #print(poly.plane.origin)
    if isinstance(poly, Circle):
        interval = 2*math.pi
        range_start = 0
        angle1 = 0

    else: # if Arc
        points.append(poly.startPoint)
        range_start = 0 

        #angle1, angle2 = getArcAngles(poly)
        
        interval, angle1, angle2 = getArcRadianAngle(poly)
        interval = abs(angle2 - angle1)
        
        #print(angle1)
        #print(angle2)
        
        if (angle1 > angle2 and normal == -1) or (angle2 > angle1 and normal == 1): pass
        if angle1 > angle2 and normal == 1: interval = abs( (2*math.pi-angle1) + angle2)
        if angle2 > angle1 and normal == -1: interval = abs( (2*math.pi-angle2) + angle1)

        #print(interval)
        #print(normal)
    
    pointsNum = math.floor( abs(interval)) * 12
    if pointsNum <4: pointsNum = 4

    for i in range(range_start, pointsNum + 1): 
        k = i/pointsNum # to reset values from 1/10 to 1
        angle = angle1 + k * interval * normal
        #print(k)
        #print(angle)
        pt = Point( x = poly.plane.origin.x + poly.radius * cos(angle), y = poly.plane.origin.y + poly.radius * sin(angle), z = 0) 
        
        pt.units = poly.plane.origin.units 
        points.append(pt)
    if isinstance(poly, Arc): points.append(poly.endPoint)
    return points


def getArcRadianAngle(arc: Arc) -> List[float]:

    interval = None
    normal = arc.plane.normal.z 
    angle1, angle2 = getArcAngles(arc)
    if angle1 is None or angle2 is  None: return None
    interval = abs(angle2 - angle1)

    if (angle1 > angle2 and normal == -1) or (angle2 > angle1 and normal == 1): pass
    if angle1 > angle2 and normal == 1: interval = abs( (2*math.pi-angle1) + angle2)
    if angle2 > angle1 and normal == -1: interval = abs( (2*math.pi-angle2) + angle1)
    return interval, angle1, angle2

def getArcAngles(poly: Arc) -> Tuple[float]: 
    
    if poly.startPoint.x == poly.plane.origin.x: angle1 = math.pi/2
    else: angle1 = atan( abs ((poly.startPoint.y - poly.plane.origin.y) / (poly.startPoint.x - poly.plane.origin.x) )) # between 0 and pi/2
    
    if poly.plane.origin.x < poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = 2*math.pi - angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y > poly.startPoint.y: angle1 = math.pi + angle1
    if poly.plane.origin.x > poly.startPoint.x and poly.plane.origin.y < poly.startPoint.y: angle1 = math.pi - angle1

    if poly.endPoint.x == poly.plane.origin.x: angle2 = math.pi/2
    else: angle2 = atan( abs ((poly.endPoint.y - poly.plane.origin.y) / (poly.endPoint.x - poly.plane.origin.x) )) # between 0 and pi/2

    if poly.plane.origin.x < poly.endPoint.x and poly.plane.origin.y > poly.endPoint.y: angle2 = 2*math.pi - angle2
    if poly.plane.origin.x > poly.endPoint.x and poly.plane.origin.y > poly.endPoint.y: angle2 = math.pi + angle2
    if poly.plane.origin.x > poly.endPoint.x and poly.plane.origin.y < poly.endPoint.y: angle2 = math.pi - angle2

    return angle1, angle2 

def getArcNormal(poly: Arc, midPt: Point): 
    print("____getArcNormal___")
    angle1, angle2 = getArcAngles(poly)

    if midPt.x == poly.plane.origin.x: angle = math.pi/2
    else: angle = atan( abs ((midPt.y - poly.plane.origin.y) / (midPt.x - poly.plane.origin.x) )) # between 0 and pi/2
    
    if poly.plane.origin.x < midPt.x and poly.plane.origin.y > midPt.y: angle = 2*math.pi - angle
    if poly.plane.origin.x > midPt.x and poly.plane.origin.y > midPt.y: angle = math.pi + angle
    if poly.plane.origin.x > midPt.x and poly.plane.origin.y < midPt.y: angle = math.pi - angle

    normal = Vector()
    normal.x = normal.y = 0

    if angle1 > angle > angle2: normal.z = -1  
    if angle1 > angle2 > angle: normal.z = 1  

    if angle2 > angle1 > angle: normal.z = -1  
    if angle > angle1 > angle2: normal.z = 1  

    if angle2 > angle > angle1: normal.z = 1  
    if angle > angle2 > angle1: normal.z = -1  
    
    print(angle1)
    print(angle)
    print(angle2)
    print(normal)

    return normal


def getArcCenter(p1: Point, p2: Point, p3: Point) -> Tuple[List, float]:
    #print(p1)
    p1 = np.array(p1.to_list())
    p2 = np.array(p2.to_list())
    p3 = np.array(p3.to_list())
    a = np.linalg.norm(p3 - p2)
    b = np.linalg.norm(p3 - p1)
    c = np.linalg.norm(p2 - p1)
    s = (a + b + c) / 2
    radius = a*b*c / 4 / np.sqrt(s * (s - a) * (s - b) * (s - c))
    b1 = a*a * (b*b + c*c - a*a)
    b2 = b*b * (a*a + c*c - b*b)
    b3 = c*c * (a*a + b*b - c*c)
    center = np.column_stack((p1, p2, p3)).dot(np.hstack((b1, b2, b3)))
    center /= b1 + b2 + b3
    center = center.tolist()
    return center, radius

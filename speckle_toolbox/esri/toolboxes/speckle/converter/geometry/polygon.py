from typing import Sequence
import arcpy 
import json 

from specklepy.objects import Base
from specklepy.objects.geometry import Point, Arc, Circle, Polycurve, Polyline, Line
from speckle.converter.geometry.mesh import rasterToMesh
from speckle.converter.geometry.point import pointToCoord
from speckle.converter.geometry.polyline import (polylineFromVerticesToSpeckle, 
                                                circleToSpeckle, 
                                                speckleArcCircleToPoints, 
                                                curveToSpeckle, 
                                                specklePolycurveToPoints,
                                                pointToNative)

import math
from panda3d.core import Triangulator


def polygonToSpeckle(geom, feature, layer, multiType: bool):
    """Converts a Polygon to Speckle"""
    #try: 
    print("___Polygon to Speckle____")
    polygon = Base(units = "m")
    pointList = []
    voidPointList = []
    voids = []
    boundary = None

    print(multiType)
    
    
        
    #else: # no curves
    if multiType is False: 
        if geom.hasCurves: 
            print("has curves")
            # geometry SHAPE@ tokens: https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/reading-geometries.htm
            print(geom.JSON) 
            boundary = curveToSpeckle(geom, "Polygon", feature, layer)
            #pts = specklePolycurveToPoints(boundary)
            #boundary = Polyline.from_points(pts)
            #coundary.closed = True 
        else: 
            print("no curves")
            for p in geom:
                for pt in p: 
                    if pt != None: pointList.append(pt) 
            boundary = polylineFromVerticesToSpeckle(pointList, True, feature, layer) 
    else: 
        print("multi type")
        for i, p in enumerate(geom):
            print(p)
            for pt in p:  
                #print(pt) # 284394.58100903 5710688.11602606 NaN NaN
                if pt == None and boundary == None:  # first break 
                    boundary = polylineFromVerticesToSpeckle(pointList, True, feature, layer) 
                    pointList = []
                elif pt == None and boundary != None: # breaks btw voids
                    void = polylineFromVerticesToSpeckle(pointList, True, feature, layer)
                    voids.append(void)
                    pointList = []
                elif pt != None: # add points to whatever list (boundary or void) 
                    pointList.append(pt)

            if boundary != None and len(pointList)>0: # remaining polyline
                void = polylineFromVerticesToSpeckle(pointList, True, feature, layer)
                voids.append(void)

    #if isinstance(boundary, Polycurve): 
    #    pts = specklePolycurveToPoints(boundary)
    #    boundary.displayValue = Polyline.from_points(pts) # + [pts[0]]) 
    #    #boundary.displayValue.closed = True

    if boundary is None: return None 
    polygon.boundary = boundary
    polygon.voids = voids
    polygon.displayValue = [ boundary ] + voids
    print(boundary)

    ############# mesh 
    vertices = []
    polyBorder = []
    total_vertices = 0
    if isinstance(boundary, Circle) or isinstance(boundary, Arc): 
        polyBorder = speckleArcCircleToPoints(boundary) 
    elif isinstance(boundary, Polycurve): 
        polyBorder = specklePolycurveToPoints(boundary) 
        #polygon.boundary.displayValue.closed = True 
    elif isinstance(boundary, Line): pass
    elif isinstance(boundary, Polyline): 
        try: polyBorder = boundary.as_points()
        except: pass # if Line
    print(polyBorder)
    

    if len(polyBorder)>2: # at least 3 points 
        print("make meshes from polygons")
        if len(voids) == 0: # if there is a mesh with no voids
            for pt in polyBorder:
                if isinstance(pt, Point): pt = pointToNative(pt)
                x = pt.x
                y = pt.y
                z = 0 if math.isnan(pt.z) else pt.z
                vertices.extend([x, y, z])
                total_vertices += 1
            #print(vertices)
            ran = range(0, total_vertices)
            faces = [total_vertices]
            faces.extend([i for i in ran])
            #print(faces)
            # else: https://docs.panda3d.org/1.10/python/reference/panda3d.core.Triangulator
        else:
            trianglator = Triangulator()
            faces = []

            # add boundary points
            #polyBorder = boundary.as_points()
            pt_count = 0
            # add extra middle point for border
            for pt in polyBorder:
              if pt_count < len(polyBorder)-1: 
                  pt2 = polyBorder[pt_count+1]
              else: pt2 = polyBorder[0]
              
              trianglator.addPolygonVertex(trianglator.addVertex(pt.x, pt.y))
              vertices.extend([pt.x, pt.y, pt.z])

              #trianglator.addPolygonVertex(trianglator.addVertex((pt.x+pt2.x)/4*3, (pt.y+pt2.y)/4*3))
              #vertices.extend([(pt.x+pt2.x)/4*3, (pt.y+pt2.y)/4*3, (pt.z+pt2.z)/4*3])

              trianglator.addPolygonVertex(trianglator.addVertex((pt.x+pt2.x)/2, (pt.y+pt2.y)/2))
              vertices.extend([(pt.x+pt2.x)/2, (pt.y+pt2.y)/2, (pt.z+pt2.z)/2])
              
              #trianglator.addPolygonVertex(trianglator.addVertex((pt.x+pt2.x)/4, (pt.y+pt2.y)/4))
              #vertices.extend([(pt.x+pt2.x)/4, (pt.y+pt2.y)/4, (pt.z+pt2.z)/4])

              total_vertices += 2
              pt_count += 1

            #add void points
            for i in range(len(voids)):
              trianglator.beginHole()


              pts = []
              if isinstance(voids[i], Circle) or isinstance(voids[i], Arc): 
                  pts = speckleArcCircleToPoints(voids[i]) 
              elif isinstance(voids[i], Polycurve): 
                  pts = specklePolycurveToPoints(voids[i]) 
              elif isinstance(voids[i], Line): pass
              else: 
                  try: pts = voids[i].as_points()
                  except: pass # if Line
              #pts = voids[i].as_points()
              for pt in pts:
                trianglator.addHoleVertex(trianglator.addVertex(pt.x, pt.y))
                vertices.extend([pt.x, pt.y, pt.z])
                total_vertices += 1

            trianglator.triangulate()
            i = 0
            while i < trianglator.getNumTriangles():
              tr = [trianglator.getTriangleV0(i),trianglator.getTriangleV1(i),trianglator.getTriangleV2(i)]
              faces.extend([3, tr[0], tr[1], tr[2]])
              i+=1
            ran = range(0, total_vertices)
        
        #print(polygon)
        col = (100<<16) + (100<<8) + 100 #featureColorfromNativeRenderer(feature, layer)
        colors = [col for i in ran] # apply same color for all vertices
        mesh = rasterToMesh(vertices, faces, colors)
        polygon.displayValue = mesh 
    #print("print resulted polygon")
    #print(polygon)
    return polygon

def polygonToNative(poly: Base, sr: arcpy.SpatialReference) -> arcpy.Polygon:
    """Converts a Speckle Polygon base object to QgsPolygon.
    This object must have a 'boundary' and 'voids' properties.
    Each being a Speckle Polyline and List of polylines respectively."""

    print("_______Drawing polygons____")
    #pts = [pointToCoord(pt) for pt in poly["boundary"].as_points()]
    pointsSpeckle = []
    if isinstance(poly["boundary"], Circle) or isinstance(poly["boundary"], Arc): 
        pointsSpeckle = speckleArcCircleToPoints(poly["boundary"]) 
    elif isinstance(poly["boundary"], Polycurve): 
        pointsSpeckle = specklePolycurveToPoints(poly["boundary"]) 
    elif isinstance(poly["boundary"], Line): pass
    else: 
        try: pointsSpeckle = poly["boundary"].as_points()
        except: pass # if Line

    pts = [pointToCoord(pt) for pt in pointsSpeckle]
    print(pts)
    outer_arr = [arcpy.Point(*coords) for coords in pts]
    outer_arr.append(outer_arr[0])
    list_of_arrs = []
    try:
        for void in poly["voids"]: 
            #print(void)
            #pts = [pointToCoord(pt) for pt in void.as_points()]
            pointsSpeckle = []
            if isinstance(void, Circle) or isinstance(void, Arc): 
                pointsSpeckle = speckleArcCircleToPoints(void) 
            elif isinstance(void, Polycurve): 
                pointsSpeckle = specklePolycurveToPoints(void) 
            elif isinstance(void, Line): pass
            else: 
                try: pointsSpeckle = void.as_points()
                except: pass # if Line
            pts = [pointToCoord(pt) for pt in pointsSpeckle]

            #print(pts)
            inner_arr = [arcpy.Point(*coords) for coords in pts]
            inner_arr.append(inner_arr[0])
            list_of_arrs.append(arcpy.Array(inner_arr))
    except:pass
    list_of_arrs.insert(0, outer_arr)
    array = arcpy.Array(list_of_arrs)
    polygon = arcpy.Polygon(array, sr, has_z=True)

    return polygon

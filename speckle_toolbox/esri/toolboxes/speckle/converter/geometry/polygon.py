from typing import Sequence
import arcpy 
import json 

from specklepy.objects import Base
from specklepy.objects.geometry import Point
from speckle.converter.geometry.mesh import rasterToMesh
from speckle.converter.geometry.point import pointToCoord
from speckle.converter.geometry.polyline import polylineFromVerticesToSpeckle, circleToSpeckle

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
    
    if geom.hasCurves: 
        # geometry SHAPE@ tokens: https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/reading-geometries.htm
        print(geom.JSON) 
        # look for "curvePaths" or "curveRings"[[ (startPt, {arcs, beziers etc}, optional(endPt))],[],...], "rings" 
        # examples: https://developers.arcgis.com/documentation/common-data-types/geometry-objects.htm
        # e.g. {"hasZ":true,"curveRings":[[[631307.05960000027,5803698.4477999993,0],{"a":[[631307.05960000027,5803698.4477999993,0],[631307.05960000027,5803414.92656173],0,1]}]],"spatialReference":{"wkid":32631,"latestWkid":32631}}
        # b - bezier curve (endPt, controlPts) 
        # a - elliptical arc (endPt, centralPt)
        # c - circular arc (endPt, throughPt) 

        #startPtCoords = geom.JSON.curveRings[0][0]
        r'''
        segments = []
        for key, val in json.loads(geom.JSON).items(): 
            if key == "curveRings": 
                for segm in val:
                    print(segm)
                    segmStartCoord = segm[0]
                    print(segmStartCoord) 

                    segmData = segm[1]
                    for key2, val2 in segmData.items():
                        if key2 == "a":
                            segmToCoord = val2[0] # elliptical arc 
                            segmCenter = val2[1]
                            print(segmToCoord)
                            print(segmCenter)
                            if segmStartCoord == segmToCoord: 
                                print("full circle") 
                                boundary = circleToSpeckle(segmCenter, segmToCoord, layer)

                            try: 
                                segmToCoord = segm[1].c # circular arc 
                            except:
                                try: 
                                    segmToCoord = segm[1].b # bezier curve 
                                except: pass

                    segmEndCoord = None
                    if len(segm)>2:
                        segmEndCoord = segm[2]
        '''

    if multiType is False: 
        print("single type")
        for p in geom:
            for pt in p: 
                if pt != None: pointList.append(pt) 
        boundary = polylineFromVerticesToSpeckle(pointList, True, feature, layer) 
    else: 
        print("multi type")
        for i, p in enumerate(geom):
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

    polygon.boundary = boundary
    polygon.voids = voids
    polygon.displayValue = [ boundary ] + voids

    ############# mesh 
    vertices = []
    total_vertices = 0
    polyBorder = boundary.as_points()

    #print(polyBorder)

    if len(polyBorder)>2:
        print("make meshes from polygons")
        if len(voids) == 0: # if there is a mesh with no voids
            for pt in polyBorder:
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
              trianglator.addPolygonVertex(trianglator.addVertex((pt.x+pt2.x)/2, (pt.y+pt2.y)/2))
              vertices.extend([(pt.x+pt2.x)/2, (pt.y+pt2.y)/2, (pt.z+pt2.z)/2])
              total_vertices += 2
              pt_count += 1

            #add void points
            for i in range(len(voids)):
              trianglator.beginHole()
              pts = voids[i].as_points()
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
    pts = [pointToCoord(pt) for pt in poly["boundary"].as_points()]
    outer_arr = [arcpy.Point(*coords) for coords in pts]
    outer_arr.append(outer_arr[0])
    list_of_arrs = []
    try:
        for void in poly["voids"]: 
            #print(void)
            pts = [pointToCoord(pt) for pt in void.as_points()]
            #print(pts)
            inner_arr = [arcpy.Point(*coords) for coords in pts]
            inner_arr.append(inner_arr[0])
            list_of_arrs.append(arcpy.Array(inner_arr))
    except:pass
    list_of_arrs.insert(0, outer_arr)
    array = arcpy.Array(list_of_arrs)
    polygon = arcpy.Polygon(array, sr, has_z=True)

    return polygon

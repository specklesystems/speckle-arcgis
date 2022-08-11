from typing import Sequence
import arcpy 

from specklepy.objects import Base
from specklepy.objects.geometry import Point
from speckle.converter.geometry.mesh import rasterToMesh
from speckle.converter.geometry.point import pointToCoord
from speckle.converter.geometry.polyline import polylineFromVerticesToSpeckle

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
    
    #print(geom) # <geoprocessing describe geometry object object at 0x0000020F1D94AB10>
    #print(multiType)

    if multiType is False: 
        for p in geom:
            #print(p) # <geoprocessing array object object at 0x0000020F1D972C90>
            for pt in p: 
                #print(pt) # 284394.58100903 5710688.11602606 NaN NaN <class 'arcpy.arcobjects.arcobjects.Point'> 
                #print(type(pt))
                if pt != None: pointList.append(pt) 
        boundary = polylineFromVerticesToSpeckle(pointList, True, feature, layer) 
    else: 
        for i, p in enumerate(geom):
            #print(i)
            #print(p) # <geoprocessing array object object at 0x00000296FFF11CF0>
            #print(type(p)) # <class 'arcpy.arcobjects.arcobjects.Array'>
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

        #print("boundary: ")
        #print(boundary)
    
    #try:
    #    for i in range(geom.numInteriorRings()):
    #        intRing = polylineFromVerticesToSpeckle(geom.interiorRing(i).vertices(), True, feature, layer)
    #        voids.append(intRing)
    #except:
    #    pass
    polygon.boundary = boundary
    polygon.voids = voids
    polygon.displayValue = [ boundary ] + voids

    ############# mesh 
    vertices = []
    total_vertices = 0
    polyBorder = boundary.as_points()

    if len(voids) == 0: # if there is a mesh with no voids
        for pt in polyBorder:
            x = pt.x
            y = pt.y
            z = 0 if math.isnan(pt.z) else pt.z
            vertices.extend([x, y, z])
            total_vertices += 1

        ran = range(0, total_vertices)
        faces = [total_vertices]
        faces.extend([i for i in ran])
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
        #print(trianglator.getNumTriangles())
        while i < trianglator.getNumTriangles():
          tr = [trianglator.getTriangleV0(i),trianglator.getTriangleV1(i),trianglator.getTriangleV2(i)]
          faces.extend([3, tr[0], tr[1], tr[2]])
          i+=1
        ran = range(0, total_vertices)

    col = (100<<16) + (100<<8) + 100 #featureColorfromNativeRenderer(feature, layer)
    colors = [col for i in ran] # apply same color for all vertices
    mesh = rasterToMesh(vertices, faces, colors)
    polygon.displayValue = mesh 

    return polygon
    #except: 
    #    arcpy.AddWarning("Some polygons might be invalid")
    #    pass

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
            print(void)
            pts = [pointToCoord(pt) for pt in void.as_points()]
            print(pts)
            inner_arr = [arcpy.Point(*coords) for coords in pts]
            inner_arr.append(inner_arr[0])
            list_of_arrs.append(arcpy.Array(inner_arr))
    except:pass
    list_of_arrs.insert(0, outer_arr)
    array = arcpy.Array(list_of_arrs)
    polygon = arcpy.Polygon(array, sr)

    return polygon

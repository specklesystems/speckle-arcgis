
from regex import F
from specklepy.objects import Base
from specklepy.objects.geometry import Line, Mesh, Point, Polyline, Curve, Arc, Circle, Polycurve, Ellipse 

import arcpy 
from typing import Any, List, Union, Sequence

import inspect 

try:
    from speckle.converter.geometry.polygon import polygonToNative, polygonToSpeckle, multiPolygonToSpeckle, polygonToSpeckleMesh
    from speckle.converter.geometry.polyline import arcToNative, ellipseToNative, circleToNative, curveToNative, lineToNative, polycurveToNative, polylineFromVerticesToSpeckle, polylineToNative, polylineToSpeckle
    from speckle.converter.geometry.point import pointToCoord, pointToNative, pointToSpeckle, multiPointToSpeckle
    from speckle.converter.geometry.polyline import speckleArcCircleToPoints, specklePolycurveToPoints, multiPolylineToSpeckle
    from speckle.ui.logger import logToUser
    from speckle.converter.geometry.mesh import meshToNative
except:
    from speckle_toolbox.esri.toolboxes.speckle.converter.geometry.polygon import polygonToNative, polygonToSpeckle, multiPolygonToSpeckle, polygonToSpeckleMesh
    from speckle_toolbox.esri.toolboxes.speckle.converter.geometry.polyline import arcToNative, ellipseToNative, circleToNative, curveToNative, lineToNative, polycurveToNative, polylineFromVerticesToSpeckle, polylineToNative, polylineToSpeckle
    from speckle_toolbox.esri.toolboxes.speckle.converter.geometry.point import pointToCoord, pointToNative, pointToSpeckle, multiPointToSpeckle
    from speckle_toolbox.esri.toolboxes.speckle.converter.geometry.polyline import speckleArcCircleToPoints, specklePolycurveToPoints, multiPolylineToSpeckle
    from speckle_toolbox.esri.toolboxes.speckle.converter.geometry.mesh import meshToNative
    from speckle_toolbox.esri.toolboxes.speckle.ui.logger import logToUser

import numpy as np

def convertToSpeckle(feature, index: str, layer, geomType, featureType) -> Union[Base, Sequence[Base], None]:
    """Converts the provided layer feature to Speckle objects"""
    print("___convertToSpeckle____________")
    try:
        geom = feature
        print(geom.isMultipart) # e.g. False 
        print(geom.partCount)
        geomMultiType = geom.isMultipart
        hasCurves = feature.hasCurves 
        
        # feature is <geoprocessing describe geometry object object at 0x000002A75D6A4BD0>
        
        #print(featureType) # e.g. Simple 
        #print(geomType) # e.g. Polygon 
        #geomSingleType = (featureType=="Simple") # Simple,SimpleJunction,SimpleJunction,ComplexEdge,Annotation,CoverageAnnotation,Dimension,RasterCatalogItem 

        if geomType == "Point": #Polygon, Point, Polyline, Multipoint, MultiPatch
            for pt in geom:
                return pointToSpeckle(pt, feature, layer)
        elif geomType == "Polyline":
            #if geom.hasCurves: 
            #    geom, feature = curvesToSegments(geom, feature, layer, geomMultiType)
            #    geomMultiType = geom.isMultipart
            #    return polylineToSpeckle(geom, feature, layer, geomMultiType)
            #else:
            if geom.partCount > 1: return multiPolylineToSpeckle(geom, feature, layer, geomMultiType)
            else: return polylineToSpeckle(geom, feature, layer, geomMultiType)
        elif geomType == "Polygon":
            if geom.partCount > 1: return multiPolygonToSpeckle(geom, index, layer, geomMultiType)
            else: return polygonToSpeckle(geom, index, layer, geomMultiType)
        elif geomType == "Multipoint":
            return multiPointToSpeckle(geom, feature, layer, geomMultiType)
        elif geomType == "MultiPatch":
            return polygonToSpeckleMesh(geom, index, layer, False)
        else:
            logToUser("Unsupported or invalid geometry in layer " + layer.name, level=1, func = inspect.stack()[0][3])
        return None
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
        return None


def convertToNative(base: Base, sr: arcpy.SpatialReference) -> Union[Any, None]:
    """Converts any given base object to QgsGeometry."""
    print("___Convert to Native SingleType___")
    converted = None
    try:
        #print(base)
        conversions = [
            (Point, pointToNative),
            (Line, lineToNative),
            (Polyline, polylineToNative),
            (Curve, curveToNative),
            (Arc, arcToNative),
            (Circle, circleToNative),
            (Ellipse, ellipseToNative),
            #(Mesh, meshToNative),
            (Polycurve, polycurveToNative),
            (Base, multiPolygonToNative), # temporary solution for polygons (Speckle has no type Polygon yet)
        ]

        for conversion in conversions:
            if isinstance(base, conversion[0]):
                #print(conversion[0])
                converted = conversion[1](base, sr)
                break
        #print(converted)
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
    return converted

def multiPointToNative(items: List[Point], sr: arcpy.SpatialReference):
    print("___Create MultiPoint")
    features = None
    try:
        all_pts = []
        # example https://pro.arcgis.com/en/pro-app/2.8/arcpy/classes/multipoint.htm
        for item in items:
            pt = pointToCoord(item) # [x, y, z]
            all_pts.append( arcpy.Point(pt[0], pt[1], pt[2]) )
        #print(all_pts)
        features = arcpy.Multipoint( arcpy.Array(all_pts) )
        #if len(features)==0: features = None
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
    return features

def multiPolylineToNative(items: List[Polyline], sr: arcpy.SpatialReference):
    print("_______Drawing Multipolylines____")
    poly = None
    try:
        #print(items)
        poly = None
        full_array_list = []
        for item in items: # will be 1 item
            pointsSpeckle = []
            try: pointsSpeckle = item.as_points()
            except: continue 
            pts = [pointToCoord(pt) for pt in pointsSpeckle]

            if item.closed is True: 
                pts.append( pointToCoord(item.as_points()[0]) )
            
            arr = [arcpy.Point(*coords) for coords in pts]
            full_array_list.append(arr)

        poly = arcpy.Polyline( arcpy.Array(full_array_list), sr, has_z=True )
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
    return poly

def multiPolygonToNative(items: List[Base], sr: arcpy.SpatialReference): #TODO fix multi features
    
    print("_______Drawing Multipolygons____")
    polygon = None 
    if not isinstance(items, List): items = [items]
    try: 
        print(items)
        full_array_list = []

        for item_geom in items: # will be 1 item
            print(item_geom)
            try: item_geom = item_geom["geometry"]
            except: item_geom = [item_geom]
            for item in item_geom:
                #print(item)
                #pts = [pointToCoord(pt) for pt in item["boundary"].as_points()]
                pointsSpeckle = []
                if isinstance(item["boundary"], Circle) or isinstance(item["boundary"], Arc): 
                    pointsSpeckle = speckleArcCircleToPoints(item["boundary"]) 
                elif isinstance(item["boundary"], Polycurve): 
                    pointsSpeckle = specklePolycurveToPoints(item["boundary"]) 
                elif isinstance(item["boundary"], Line): pass
                else: 
                    try: pointsSpeckle = item["boundary"].as_points()
                    except Exception as e: print(e) # if Line
                #print(pointsSpeckle)
                pts = [pointToCoord(pt) for pt in pointsSpeckle]
                #print(pts)

                outer_arr = [arcpy.Point(*coords) for coords in pts]
                outer_arr.append(outer_arr[0])
                #print(outer_arr)
                geomPart = []
                try:
                    for void in item["voids"]: 
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

                        inner_arr = [arcpy.Point(*coords) for coords in pts]
                        inner_arr.append(inner_arr[0])
                        geomPart.append(arcpy.Array(inner_arr))
                except Exception as e: print(e)
                geomPart.insert(0, arcpy.Array(outer_arr))
                
                #print(geomPart)
                full_array_list.extend(geomPart) # outlines are written one by one, with no separation to "parts"
            #print("end of loop1")
        print("end of loop2")
        geomPartArray = arcpy.Array(full_array_list)
        polygon = arcpy.Polygon(geomPartArray, sr, has_z=True)
        
        print(polygon)
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
    
    return polygon

def convertToNativeMulti(items: List[Base], sr: arcpy.SpatialReference): 
    print("___Convert to Native MultiType___")
    try:
        first = items[0]
        if isinstance(first, Point):
            return multiPointToNative(items, sr)
        elif isinstance(first, Line) or isinstance(first, Polyline):
            return multiPolylineToNative(items, sr)
        elif isinstance(first, Base): 
            try:
                if first["boundary"] is not None and first["voids"] is not None:
                    return multiPolygonToNative(items, sr)
            except: return None 
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
        return None 
    

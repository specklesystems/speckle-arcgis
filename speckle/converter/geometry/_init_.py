
from regex import F
from specklepy.objects import Base
from specklepy.objects.geometry import Line, Mesh, Point, Polyline, Curve, Arc, Circle, Polycurve

import arcpy 
from typing import List, Union, Sequence
from speckle.converter.geometry.polygon import polygonToSpeckle
from speckle.converter.geometry.polyline import polylineFromVerticesToSpeckle
from speckle.converter.geometry.point import pointToSpeckle


def convertToSpeckle(feature, layer, geomType, featureType) -> Union[Base, Sequence[Base], None]:
    """Converts the provided layer feature to Speckle objects"""
    print("___convertToSpeckle___")
    geom = feature
    print(featureType)
    geomSingleType = (featureType=="Simple") # Simple,SimpleJunction,SimpleJunction,ComplexEdge,Annotation,CoverageAnnotation,Dimension,RasterCatalogItem 

    if geomType == "Point": #Polygon, Point, Polyline, Multipoint, MultiPatch
        if geomSingleType:
            for pt in geom:
                return pointToSpeckle(pt, feature, layer)
    elif geomType == "Polyline":
        if geomSingleType:
            vertices = []
            for p in geom:
                for pt in p: # <class 'arcpy.arcobjects.arcobjects.Point'>
                    #ptGeometry = arcpy.PointGeometry(point)
                    vertices.append(pt)
            return polylineFromVerticesToSpeckle(vertices, False, feature, layer)
    elif geomType == "Polygon":
        if geomSingleType:
            return polygonToSpeckle(geom, feature, layer)
    elif geomType == "Multipoint":
        print(feature)
        arcpy.AddWarning("Unsupported or invalid geometry in layer " + layer.name)
    else:
        arcpy.AddWarning("Unsupported or invalid geometry in layer " + layer.name)
    return None



from typing import List, Union
from specklepy.objects.geometry import Point, Line, Polyline, Curve, Arc, Circle, Polycurve
import arcpy 

from speckle.converter.geometry.point import pointToSpeckle


def polylineFromVerticesToSpeckle(vertices, closed, feature, layer):
    """Returns a Speckle Polyline given a list of QgsPoint instances and a boolean indicating if it's closed or not."""
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
    '''
    col = featureColorfromNativeRenderer(feature, layer)
    polyline['displayStyle'] = {}
    polyline['displayStyle']['color'] = col
    '''
    return polyline


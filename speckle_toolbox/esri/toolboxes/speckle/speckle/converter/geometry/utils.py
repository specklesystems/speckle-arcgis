import math
from math import cos, sin, atan
import numpy as np
from specklepy.objects.geometry import (
    Point,
    Line,
    Polyline,
    Circle,
    Arc,
    Polycurve,
    Vector,
)
from specklepy.objects import Base
from typing import List, Tuple, Union

import inspect

from speckle.speckle.utils.panel_logging import logToUser


def addCorrectUnits(geom: Base, dataStorage) -> Base:
    if not isinstance(geom, Base):
        return None
    units = dataStorage.currentUnits

    geom.units = units
    if isinstance(geom, Arc):
        geom.plane.origin.units = units
        geom.startPoint.units = units
        geom.midPoint.units = units
        geom.endPoint.units = units

    elif isinstance(geom, Polycurve):
        for s in geom.segments:
            s.units = units
            if isinstance(s, Arc):
                s.plane.origin.units = units
                s.startPoint.units = units
                s.midPoint.units = units
                s.endPoint.units = units

    return geom


def apply_pt_offsets_rotation_on_send(
    x: float, y: float, dataStorage
) -> Tuple[Union[float, None], Union[float, None]]:  # on Send
    try:
        offset_x = dataStorage.crs_offset_x
        offset_y = dataStorage.crs_offset_y
        rotation = dataStorage.crs_rotation
        if offset_x is not None and isinstance(offset_x, float):
            x -= offset_x
        if offset_y is not None and isinstance(offset_y, float):
            y -= offset_y
        if (
            rotation is not None
            and (isinstance(rotation, float) or isinstance(rotation, int))
            and -360 < rotation < 360
        ):
            a = rotation * math.pi / 180
            x2 = x * math.cos(a) + y * math.sin(a)
            y2 = -x * math.sin(a) + y * math.cos(a)
            x = x2
            y = y2
        return x, y
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None, None


def transform_speckle_pt_on_receive(pt_original: Point, dataStorage) -> Point:
    offset_x = dataStorage.crs_offset_x
    offset_y = dataStorage.crs_offset_y
    rotation = dataStorage.crs_rotation

    pt = Point(
        x=pt_original.x, y=pt_original.y, z=pt_original.z, units=pt_original.units
    )

    gisLayer = None
    try:
        gisLayer = dataStorage.latestHostApp.lower().endswith("gis")
        applyTransforms = False if (gisLayer and gisLayer is True) else True
    except Exception as e:
        print(e)
        applyTransforms = True

    # for non-GIS layers
    if applyTransforms is True:
        if (
            rotation is not None
            and (isinstance(rotation, float) or isinstance(rotation, int))
            and -360 < rotation < 360
        ):
            a = rotation * math.pi / 180
            x2 = pt.x
            y2 = pt.y

            # if a > 0: # turn counterclockwise on receive
            x2 = pt.x * math.cos(a) - pt.y * math.sin(a)
            y2 = pt.x * math.sin(a) + pt.y * math.cos(a)

            pt.x = x2
            pt.y = y2
        if (
            offset_x is not None
            and isinstance(offset_x, float)
            and offset_y is not None
            and isinstance(offset_y, float)
        ):
            pt.x += offset_x
            pt.y += offset_y

    # for GIS layers
    if gisLayer is True:
        try:
            offset_x = dataStorage.current_layer_crs_offset_x
            offset_y = dataStorage.current_layer_crs_offset_y
            rotation = dataStorage.current_layer_crs_rotation

            if (
                rotation is not None
                and isinstance(rotation, float)
                and -360 < rotation < 360
            ):
                a = rotation * math.pi / 180
                x2 = pt.x
                y2 = pt.y

                # if a > 0: # turn counterclockwise on receive
                x2 = pt.x * math.cos(a) - pt.y * math.sin(a)
                y2 = pt.x * math.sin(a) + pt.y * math.cos(a)

                pt.x = x2
                pt.y = y2
            if (
                offset_x is not None
                and isinstance(offset_x, float)
                and offset_y is not None
                and isinstance(offset_y, float)
            ):
                pt.x += offset_x
                pt.y += offset_y
        except Exception as e:
            print(e)

    return pt


def apply_pt_transform_matrix(pt_coords: List, dataStorage) -> List:
    try:
        if dataStorage.matrix is not None:
            b = np.matrix(pt_coords + [1])
            # print(b)
            # print(dataStorage.matrix)
            res = b * dataStorage.matrix
            x, y, z = res.item(0), res.item(1), res.item(2)
            return [x, y, z]
    except Exception as e:
        pass
        # print(e)
    return pt_coords


def speckleBoundaryToSpecklePts(
    boundary: Union[None, Polyline, Arc, Line, Polycurve]
) -> List[Point]:
    # print("__speckleBoundaryToSpecklePts__")
    # add boundary points
    polyBorder = []
    try:
        if isinstance(boundary, Circle) or isinstance(boundary, Arc):
            polyBorder = speckleArcCircleToPoints(boundary)
        elif isinstance(boundary, Polycurve):
            polyBorder = specklePolycurveToPoints(boundary)
        elif isinstance(boundary, Line):
            pass
        else:
            try:
                polyBorder = boundary.as_points()
            except:
                pass  # if Line or None
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return polyBorder


def speckleArcCircleToPoints(poly: Union[Arc, Circle]) -> List[Point]:
    print("__Arc or Circle to Points___")
    points = []
    try:
        # print(poly.plane)
        # print(poly.plane.normal)
        if poly.plane is None or poly.plane.normal.z == 0:
            normal = 1
        else:
            normal = poly.plane.normal.z
        # print(poly.plane.origin)
        if isinstance(poly, Circle):
            interval = 2 * math.pi
            range_start = 0
            angle1 = 0

        else:  # if Arc
            points.append(poly.startPoint)
            range_start = 0

            # angle1, angle2 = getArcAngles(poly)

            interval, angle1, angle2 = getArcRadianAngle(poly)
            interval = abs(angle2 - angle1)

            # print(angle1)
            # print(angle2)

            if (angle1 > angle2 and normal == -1) or (angle2 > angle1 and normal == 1):
                pass
            if angle1 > angle2 and normal == 1:
                interval = abs((2 * math.pi - angle1) + angle2)
            if angle2 > angle1 and normal == -1:
                interval = abs((2 * math.pi - angle2) + angle1)

            # print(interval)
            # print(normal)

        pointsNum = math.floor(abs(interval)) * 12
        if pointsNum < 4:
            pointsNum = 4

        for i in range(range_start, pointsNum + 1):
            k = i / pointsNum  # to reset values from 1/10 to 1
            angle = angle1 + k * interval * normal
            # print(k)
            # print(angle)
            pt = Point(
                x=poly.plane.origin.x + poly.radius * cos(angle),
                y=poly.plane.origin.y + poly.radius * sin(angle),
                z=0,
            )

            pt.units = poly.plane.origin.units
            points.append(pt)
        if isinstance(poly, Arc):
            points.append(poly.endPoint)
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return points


def getArcRadianAngle(arc: Arc) -> List[float]:
    try:
        interval = None
        normal = arc.plane.normal.z
        angle1, angle2 = getArcAngles(arc)
        if angle1 is None or angle2 is None:
            return None
        interval = abs(angle2 - angle1)

        if (angle1 > angle2 and normal == -1) or (angle2 > angle1 and normal == 1):
            pass
        if angle1 > angle2 and normal == 1:
            interval = abs((2 * math.pi - angle1) + angle2)
        if angle2 > angle1 and normal == -1:
            interval = abs((2 * math.pi - angle2) + angle1)
        return interval, angle1, angle2
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None, None, None


def getArcAngles(poly: Arc) -> Tuple[float]:
    try:
        if poly.startPoint.x == poly.plane.origin.x:
            angle1 = math.pi / 2
        else:
            angle1 = atan(
                abs(
                    (poly.startPoint.y - poly.plane.origin.y)
                    / (poly.startPoint.x - poly.plane.origin.x)
                )
            )  # between 0 and pi/2

        if (
            poly.plane.origin.x < poly.startPoint.x
            and poly.plane.origin.y > poly.startPoint.y
        ):
            angle1 = 2 * math.pi - angle1
        if (
            poly.plane.origin.x > poly.startPoint.x
            and poly.plane.origin.y > poly.startPoint.y
        ):
            angle1 = math.pi + angle1
        if (
            poly.plane.origin.x > poly.startPoint.x
            and poly.plane.origin.y < poly.startPoint.y
        ):
            angle1 = math.pi - angle1

        if poly.endPoint.x == poly.plane.origin.x:
            angle2 = math.pi / 2
        else:
            angle2 = atan(
                abs(
                    (poly.endPoint.y - poly.plane.origin.y)
                    / (poly.endPoint.x - poly.plane.origin.x)
                )
            )  # between 0 and pi/2

        if (
            poly.plane.origin.x < poly.endPoint.x
            and poly.plane.origin.y > poly.endPoint.y
        ):
            angle2 = 2 * math.pi - angle2
        if (
            poly.plane.origin.x > poly.endPoint.x
            and poly.plane.origin.y > poly.endPoint.y
        ):
            angle2 = math.pi + angle2
        if (
            poly.plane.origin.x > poly.endPoint.x
            and poly.plane.origin.y < poly.endPoint.y
        ):
            angle2 = math.pi - angle2

        return angle1, angle2

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None, None


def specklePolycurveToPoints(poly: Polycurve) -> List[Point]:
    print("_____Speckle Polycurve to points____")
    points = []
    try:
        for segm in poly.segments:
            # print(segm)
            pts = []
            if isinstance(segm, Arc) or isinstance(
                segm, Circle
            ):  # or isinstance(segm, Curve):
                print("Arc or Curve")
                pts: List[Point] = speckleArcCircleToPoints(segm)
            elif isinstance(segm, Line):
                print("Line")
                pts: List[Point] = [segm.start, segm.end]
            elif isinstance(segm, Polyline):
                print("Polyline")
                pts: List[Point] = segm.as_points()

            points.extend(pts)

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return points


def getArcNormal(poly: Arc, midPt: Point):
    print("____getArcNormal___")
    try:
        angle1, angle2 = getArcAngles(poly)

        if midPt.x == poly.plane.origin.x:
            angle = math.pi / 2
        else:
            angle = atan(
                abs((midPt.y - poly.plane.origin.y) / (midPt.x - poly.plane.origin.x))
            )  # between 0 and pi/2

        if poly.plane.origin.x < midPt.x and poly.plane.origin.y > midPt.y:
            angle = 2 * math.pi - angle
        if poly.plane.origin.x > midPt.x and poly.plane.origin.y > midPt.y:
            angle = math.pi + angle
        if poly.plane.origin.x > midPt.x and poly.plane.origin.y < midPt.y:
            angle = math.pi - angle

        normal = Vector()
        normal.x = normal.y = 0

        if angle1 > angle > angle2:
            normal.z = -1
        if angle1 > angle2 > angle:
            normal.z = 1

        if angle2 > angle1 > angle:
            normal.z = -1
        if angle > angle1 > angle2:
            normal.z = 1

        if angle2 > angle > angle1:
            normal.z = 1
        if angle > angle2 > angle1:
            normal.z = -1

        print(angle1)
        print(angle)
        print(angle2)
        print(normal)
        return normal
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None


def getArcCenter(p1: Point, p2: Point, p3: Point) -> Tuple[List, float]:
    # print(p1)
    try:
        p1 = np.array(p1.to_list())
        p2 = np.array(p2.to_list())
        p3 = np.array(p3.to_list())
        a = np.linalg.norm(p3 - p2)
        b = np.linalg.norm(p3 - p1)
        c = np.linalg.norm(p2 - p1)
        s = (a + b + c) / 2
        radius = a * b * c / 4 / np.sqrt(s * (s - a) * (s - b) * (s - c))
        b1 = a * a * (b * b + c * c - a * a)
        b2 = b * b * (a * a + c * c - b * b)
        b3 = c * c * (a * a + b * b - c * c)
        center = np.column_stack((p1, p2, p3)).dot(np.hstack((b1, b2, b3)))
        center /= b1 + b2 + b3
        center = center.tolist()
        return center, radius
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None, None

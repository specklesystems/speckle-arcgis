from datetime import datetime
import inspect
import math
import os
from typing import List, Union
import arcpy
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer

import numpy as np

import scipy as sp
from speckle.speckle.plugin_utils.helpers import (
    findOrCreatePath,
    get_scale_factor_to_meter,
)
from speckle.speckle.converter.layers.utils import (
    findTransformation,
    getVariantFromValue,
    traverseDict,
    validateAttributeName,
)

# from speckle.speckle.converter.geometry.conversions import transform
from speckle.speckle.converter.geometry.conversions import (
    convertToNative,
    convertToNativeMulti,
    convertToSpeckle,
)
from speckle.speckle.converter.geometry.mesh import constructMeshFromRaster
from speckle.speckle.converter.geometry.utils import apply_pt_offsets_rotation_on_send
from speckle.speckle.utils.panel_logging import logToUser
from speckle.speckle.converter.features.utils import updateFeat
from specklepy.objects.GIS.geometry import (
    GisRasterElement,
    GisPolygonGeometry,
    GisNonGeometryElement,
    GisTopography,
)

from specklepy.objects import Base

from speckle.speckle.converter.geometry.point import pointToSpeckle
from speckle.speckle.converter.layers.symbology import jsonFromLayerStyle


def featureToSpeckle(
    fieldnames,
    attr_list,
    index: int,
    f_shape,
    projectCRS: arcpy.SpatialReference,
    selectedLayer: arcLayer,
    plugin,
):
    dataStorage = plugin.dataStorage
    if dataStorage is None:
        return
    units = dataStorage.currentUnits
    new_report = {"obj_type": "", "errors": ""}
    iterations = 0
    try:
        geom = None
        data = arcpy.Describe(selectedLayer.dataSource)
        geomType = data.shapeType
        if (
            hasattr(data, "isRevit")
            or hasattr(data, "isIFC")
            or hasattr(data, "bimLevels")
        ):
            # print(f"Layer {selectedLayer.name} has unsupported data type")
            logToUser(
                f"Layer {selectedLayer.name} has unsupported data type",
                level=1,
                func=inspect.stack()[0][3],
            )
            return None

        skipped_msg = f"'{geomType}' feature skipped due to invalid geometry"
        try:
            geom, iterations = convertToSpeckle(
                f_shape, index, selectedLayer, data, dataStorage
            )
            print(geom)
            if geom is not None and geom != "None":
                if not isinstance(geom.geometry, List):
                    logToUser(
                        "Geometry not in list format",
                        level=2,
                        func=inspect.stack()[0][3],
                    )
                    return None

                all_errors = ""
                for g in geom.geometry:
                    if g is None or g == "None":
                        all_errors += skipped_msg + ", "
                        logToUser(skipped_msg, level=2, func=inspect.stack()[0][3])
                    elif isinstance(g, GisPolygonGeometry):
                        if len(g.displayValue) == 0:
                            all_errors += (
                                "Polygon converted, but display mesh not generated"
                                + ", "
                            )
                            logToUser(
                                "Polygon converted, but display mesh not generated",
                                level=1,
                                func=inspect.stack()[0][3],
                            )
                        elif iterations is not None and iterations > 0:
                            all_errors += "Polygon display mesh is simplified" + ", "
                            logToUser(
                                "Polygon display mesh is simplified",
                                level=1,
                                func=inspect.stack()[0][3],
                            )

                if len(geom.geometry) == 0:
                    all_errors = "No geometry converted"
                new_report.update({"obj_type": geom.speckle_type, "errors": all_errors})

            else:  # geom is None
                new_report = {"obj_type": "", "errors": skipped_msg}
                logToUser(skipped_msg, level=2, func=inspect.stack()[0][3])

                dataStorage.latestActionFeaturesReport[
                    len(dataStorage.latestActionFeaturesReport) - 1
                ].update(new_report)
                return
                # geom = GisNonGeometryElement()
        except Exception as error:
            new_report = {
                "obj_type": "",
                "errors": "Error converting geometry: " + str(error),
            }
            logToUser(
                "Error converting geometry: " + str(error),
                level=2,
                func=inspect.stack()[0][3],
            )

        # print(fieldnames)
        # print(attr_list)
        attributes = Base()
        for i, name in enumerate(fieldnames):
            corrected = validateAttributeName(name, fieldnames)
            # print(corrected)
            f_val = attr_list[i]
            if f_val == "NULL" or f_val is None or str(f_val) == "NULL":
                f_val = None
            if isinstance(attr_list[i], list):
                x = ""
                for i, attr in enumerate(attr_list[i]):
                    if i == 0:
                        x += str(attr)
                    else:
                        x += ", " + str(attr)
                f_val = x
            attributes[corrected] = f_val

        if geom is not None and geom != "None":
            geom.attributes = attributes
        # print(geom.attributes)

        dataStorage.latestActionFeaturesReport[
            len(dataStorage.latestActionFeaturesReport) - 1
        ].update(new_report)
        return geom

    except Exception as e:
        new_report.update({"errors": e})
        dataStorage.latestActionFeaturesReport[
            len(dataStorage.latestActionFeaturesReport) - 1
        ].update(new_report)
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return geom


def rasterFeatureToSpeckle(
    selectedLayer: arcLayer,
    projectCRS: arcpy.SpatialReference,
    plugin,
) -> Base:
    dataStorage = plugin.dataStorage
    if dataStorage is None:
        return

    b = GisRasterElement(units=dataStorage.currentUnits)
    try:
        # get Raster object of entire raster dataset
        my_raster = arcpy.Raster(selectedLayer.dataSource)
        print(my_raster.mdinfo)  # None

        rasterBandCount = my_raster.bandCount
        rasterBandNames = my_raster.bandNames
        rasterDimensions = [my_raster.width, my_raster.height]
        print(rasterDimensions)

        # ds = gdal.Open(selectedLayer.source(), gdal.GA_ReadOnly)
        extent = my_raster.extent
        print(extent.XMin)
        print(extent.YMin)
        rasterOriginPoint = arcpy.PointGeometry(
            arcpy.Point(extent.XMin, extent.YMax, extent.ZMin),
            my_raster.spatialReference,
            has_z=True,
        )

        # if extent.YMin>0: rasterOriginPoint = arcpy.PointGeometry(arcpy.Point(extent.XMin, extent.YMax, extent.ZMin), my_raster.spatialReference, has_z = True)
        print(rasterOriginPoint)
        rasterResXY = [
            my_raster.meanCellWidth,
            my_raster.meanCellHeight,
        ]  # [float(ds.GetGeoTransform()[1]), float(ds.GetGeoTransform()[5])]
        rasterBandNoDataVal = []  # list(my_raster.noDataValues)
        rasterBandMinVal = []
        rasterBandMaxVal = []
        rasterBandVals = []

        # Try to extract geometry
        reprojectedPt = None
        try:
            reprojectedPt = rasterOriginPoint
            if my_raster.spatialReference.name != projectCRS.name:
                reprojectedPt = findTransformation(
                    reprojectedPt,
                    "Point",
                    my_raster.spatialReference,
                    projectCRS,
                    selectedLayer,
                )
                if reprojectedPt is None:
                    reprojectedPt = rasterOriginPoint
        except Exception as error:
            logToUser(
                "Error converting point geometry: " + str(error),
                level=2,
                func=inspect.stack()[0][3],
            )

        for index in range(rasterBandCount):
            item = rasterBandNames[index]

            rb = my_raster.getRasterBands(item)
            print(rb)
            size = np.shape(rb.read())
            print(size)
            rasterDimensions = [size[1], size[0]]

            valMin = rb.minimum
            valMax = rb.maximum
            bandVals = np.swapaxes(rb.read(), 1, 2).flatten()  # .tolist() np.flip( , 0)

            bandValsFlat = bandVals.tolist()
            # print(bandValsFlat)

            const = float(-1 * math.pow(10, 30))
            defaultNoData = rb.noDataValue
            print(defaultNoData)

            # check whether NA value is too small or raster has too small values
            # assign min value of an actual list; re-assign NA val; replace list items to new NA val
            try:
                # create "safe" fake NA value; replace extreme values with it
                fakeNA = max(bandValsFlat) + 1
                bandValsFlatFake = [
                    fakeNA if val <= const else val for val in bandValsFlat
                ]  # replace all values corresponding to NoData value

                # if default NA value is too small
                if (
                    isinstance(defaultNoData, float) or isinstance(defaultNoData, int)
                ) and defaultNoData < const:
                    # find and rewrite min of actual band values; create new NA value
                    valMin = min(bandValsFlatFake)
                    noDataValNew = valMin - 1000  # use new adequate value
                    rasterBandNoDataVal.append(noDataValNew)
                    # replace fake NA with new NA
                    bandValsFlat = [
                        noDataValNew if val == fakeNA else val
                        for val in bandValsFlatFake
                    ]  # replace all values corresponding to NoData value

                # if default val unaccessible and minimum val is too small
                elif (
                    isinstance(defaultNoData, str) or defaultNoData is None
                ) and valMin < const:  # if there are extremely small values but default NA unaccessible
                    noDataValNew = valMin
                    rasterBandNoDataVal.append(noDataValNew)
                    # replace fake NA with new NA
                    bandValsFlat = [
                        noDataValNew if val == fakeNA else val
                        for val in bandValsFlatFake
                    ]  # replace all values corresponding to NoData value
                    # last, change minValto actual one
                    valMin = min(bandValsFlatFake)

                else:
                    rasterBandNoDataVal.append(rb.noDataValue)

            except:
                rasterBandNoDataVal.append(rb.noDataValue)

            # if rasterBandNoDataVal[len(rasterBandNoDataVal) - 1] is None:
            #   rasterBandNoDataVal[len(rasterBandNoDataVal) - 1] = np.nan
            print(len(bandValsFlat))
            rasterBandVals.append(bandValsFlat)
            rasterBandMinVal.append(valMin)
            rasterBandMaxVal.append(valMax)

            b["@(10000)" + item + "_values"] = (
                bandValsFlat  # [0:int(max_values/rasterBandCount)]
            )

        b.x_resolution = rasterResXY[0]
        b.y_resolution = -1 * rasterResXY[1]
        b.x_size = rasterDimensions[0]
        b.y_size = rasterDimensions[1]
        b.x_origin, b.y_origin = apply_pt_offsets_rotation_on_send(
            reprojectedPt.getPart().X, reprojectedPt.getPart().Y, dataStorage
        )
        b.band_count = rasterBandCount
        b.band_names = rasterBandNames
        try:
            b.noDataValue = [float(val) for val in rasterBandNoDataVal]
        except:
            pass
        # creating a mesh
        vertices = []
        faces = []
        colors = []
        count = 0

        # print(selectedLayer.symbology)  # None
        colorizer = None

        # print(rendererType)
        # identify symbology type and if Multiband, which band is which color

        #############################################################

        largeTransform = False
        if rasterDimensions[0] * rasterDimensions[1] > 10000:
            logToUser(
                f"Transformation of the layer '{selectedLayer.name}' might take a while 🕒",
                level=0,
                plugin=plugin.dockwidget,
            )
            largeTransform = True

        ############################################################

        if hasattr(selectedLayer.symbology, "colorizer"):
            colorizer = selectedLayer.symbology.colorizer
            # print(
            #    colorizer
            # )  # <arcpy._colorizer.RasterStretchColorizer object at 0x000001780497FBC8>
            # print(colorizer.type)  # RasterStretchColorizer
        else:
            redBand = greenBand = blueBand = None
            # RGB colorizer
            root_path: str = (
                os.path.expandvars(r"%LOCALAPPDATA%")
                + "\\Temp\\Speckle_ArcGIS_temp\\"
                + datetime.now().strftime("%Y-%m-%d_%H-%M")
            )
            root_path += "\\Layers_Speckle\\raster_bands\\"
            findOrCreatePath(root_path)

            # if not os.path.exists(root_path + '\\Layers_Speckle\\raster_bands'): os.makedirs(root_path + '\\Layers_Speckle\\raster_bands')
            path_style = root_path + selectedLayer.name + "_temp.lyrx"
            symJson = jsonFromLayerStyle(selectedLayer, path_style)

            # read from Json
            try:
                greenBand = symJson["layerDefinitions"][0]["colorizer"][
                    "greenBandIndex"
                ]
            except:
                if len(rasterBandVals) > 1:
                    greenBand = 1
            try:
                blueBand = symJson["layerDefinitions"][0]["colorizer"]["blueBandIndex"]
            except:
                if len(rasterBandVals) > 2:
                    blueBand = 2
            try:
                redBand = symJson["layerDefinitions"][0]["colorizer"]["redBandIndex"]
            except:
                if blueBand != 0 and greenBand != 0:
                    redBand = 0
                else:
                    redBand = None
            print("bands")
            print(redBand)
            print(greenBand)
            print(blueBand)
            try:
                rbVals = rasterBandVals[
                    redBand
                ]  # my_raster.getRasterBands(rasterBandNames[redBand])
                rbvalMin = rasterBandMinVal[redBand]
                rbvalMax = rasterBandMaxVal[redBand]
                rvalRange = float(rbvalMax) - float(rbvalMin)
                print(rbvalMin)
                print(rbvalMax)
                print(rvalRange)
            except Exception as e:
                print(e)
                rvalRange = None
            try:
                gbVals = rasterBandVals[greenBand]
                gbvalMin = rasterBandMinVal[greenBand]
                gbvalMax = rasterBandMaxVal[greenBand]
                gvalRange = float(gbvalMax) - float(gbvalMin)
                print(gbvalMin)
                print(gbvalMax)
                print(gvalRange)
            except:
                gvalRange = None
            try:
                bbVals = rasterBandVals[blueBand]
                bbvalMin = rasterBandMinVal[blueBand]
                bbvalMax = rasterBandMaxVal[blueBand]
                bvalRange = float(bbvalMax) - float(bbvalMin)
                print(bbvalMin)
                print(bbvalMax)
                print(bvalRange)
            except:
                bvalRange = None

        rendererType = ""
        bandIndex = 0

        array_z = []  # size is large by 1 than the raster size, in both dimensions
        time0 = datetime.now()

        print(projectCRS)
        print(projectCRS.factoryCode)
        if isinstance(projectCRS.factoryCode, int) and projectCRS.factoryCode > 1:
            reprojected_raster = arcpy.ia.Reproject(
                my_raster, {"wkid": projectCRS.factoryCode}
            )
        print(my_raster.spatialReference)
        print(my_raster.spatialReference.factoryCode)
        for v in range(rasterDimensions[1]):  # each row, Y
            print(v)
            if largeTransform is True:
                if v == int(rasterDimensions[1] / 20):
                    logToUser(
                        f"Converting layer '{selectedLayer.name}': 5%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] / 10):
                    logToUser(
                        f"Converting layer '{selectedLayer.name}': 10%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] / 5):
                    logToUser(
                        f"Converting layer '{selectedLayer.name}': 20%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] * 2 / 5):
                    logToUser(
                        f"Converting layer '{selectedLayer.name}': 40%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] * 3 / 5):
                    logToUser(
                        f"Converting layer '{selectedLayer.name}': 60%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] * 4 / 5):
                    logToUser(
                        f"Converting layer '{selectedLayer.name}': 80%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )
                elif v == int(rasterDimensions[1] * 9 / 10):
                    logToUser(
                        f"Converting layer '{selectedLayer.name}': 90%...",
                        level=0,
                        plugin=plugin.dockwidget,
                    )

            for h in range(rasterDimensions[0]):  # item in a row, X

                pt1 = arcpy.PointGeometry(
                    arcpy.Point(
                        extent.XMin + h * rasterResXY[0],
                        extent.YMax - v * rasterResXY[1],
                    ),
                    my_raster.spatialReference,
                    has_z=True,
                )
                pt2 = arcpy.PointGeometry(
                    arcpy.Point(
                        extent.XMin + h * rasterResXY[0],
                        extent.YMax - (v + 1) * rasterResXY[1],
                    ),
                    my_raster.spatialReference,
                    has_z=True,
                )
                pt3 = arcpy.PointGeometry(
                    arcpy.Point(
                        extent.XMin + (h + 1) * rasterResXY[0],
                        extent.YMax - (v + 1) * rasterResXY[1],
                    ),
                    my_raster.spatialReference,
                    has_z=True,
                )
                pt4 = arcpy.PointGeometry(
                    arcpy.Point(
                        extent.XMin + (h + 1) * rasterResXY[0],
                        extent.YMax - v * rasterResXY[1],
                    ),
                    my_raster.spatialReference,
                    has_z=True,
                )

                # first, get point coordinates with correct position and resolution, then reproject each:
                if (
                    my_raster.spatialReference.exportToString()
                    != projectCRS.exportToString()
                ):
                    pt1 = findTransformation(
                        pt1,
                        "Point",
                        my_raster.spatialReference,
                        projectCRS,
                        selectedLayer,
                    )
                    pt2 = findTransformation(
                        pt2,
                        "Point",
                        my_raster.spatialReference,
                        projectCRS,
                        selectedLayer,
                    )
                    pt3 = findTransformation(
                        pt3,
                        "Point",
                        my_raster.spatialReference,
                        projectCRS,
                        selectedLayer,
                    )
                    pt4 = findTransformation(
                        pt4,
                        "Point",
                        my_raster.spatialReference,
                        projectCRS,
                        selectedLayer,
                    )
                vertices.extend(
                    [
                        pt1.getPart().X,
                        pt1.getPart().Y,
                        pt1.getPart().Z,
                        pt2.getPart().X,
                        pt2.getPart().Y,
                        pt2.getPart().Z,
                        pt3.getPart().X,
                        pt3.getPart().Y,
                        pt3.getPart().Z,
                        pt4.getPart().X,
                        pt4.getPart().Y,
                        pt4.getPart().Z,
                    ]
                )  ## add 4 points
                faces.extend([4, count, count + 1, count + 2, count + 3])

                # color vertices according to QGIS renderer
                color = (0 << 16) + (0 << 8) + 0
                noValColor = (
                    0,
                    0,
                    0,
                )

                if hasattr(selectedLayer.symbology, "colorizer"):  # only 1 band
                    try:
                        bandIndex = int(colorizer.band)  # if stretched
                    except:
                        pass
                    if colorizer.type == "RasterUniqueValueColorizer":
                        # REDO !!!!!!!!!!!!
                        colorRVal = colorGVal = colorBVal = 0
                        try:
                            for br in colorizer.groups:
                                print(br.heading)  # "Value"
                                # go through all values classified
                                if br.heading != "Value":
                                    print(int("x"))  # call exception
                                for k, itm in enumerate(br.items):
                                    print(itm.values)
                                    if (
                                        itm.values[0]
                                        == rasterBandVals[bandIndex][int(count / 4)]
                                    ):
                                        print(itm.values[0])
                                        colorRVal, colorGVal, colorBVal = (
                                            itm.color["RGB"][0],
                                            itm.color["RGB"][1],
                                            itm.color["RGB"][2],
                                        )
                                        break
                                    # if string covering float
                                    try:
                                        if float(itm.values[0]) == float(
                                            rasterBandVals[bandIndex][int(count / 4)]
                                        ):
                                            print(itm.values[0])
                                            colorRVal, colorGVal, colorBVal = (
                                                itm.color["RGB"][0],
                                                itm.color["RGB"][1],
                                                itm.color["RGB"][2],
                                            )
                                            break
                                    except Exception as e:
                                        print(e)
                                        pass

                        except Exception as e:  # if no Min Max labels:
                            # REMAP band values to (0,255) range
                            print(e)
                            valRange = max(rasterBandVals[bandIndex]) - min(
                                rasterBandVals[bandIndex]
                            )  # (rasterBandMaxVal[bandIndex] - rasterBandMinVal[bandIndex])
                            if valRange == 0:
                                if min(rasterBandVals[bandIndex]) == 0:
                                    colorVal = 0
                                else:
                                    colorVal = 255
                            else:
                                colorRVal = colorGVal = colorBVal = int(
                                    (
                                        rasterBandVals[bandIndex][int(count / 4)]
                                        - min(rasterBandVals[bandIndex])
                                    )
                                    / valRange
                                    * 255
                                )

                        color = (colorRVal << 16) + (colorGVal << 8) + colorBVal

                    else:
                        try:
                            if rasterBandVals[bandIndex][int(count / 4)] >= float(
                                colorizer.minLabel
                            ) and rasterBandVals[bandIndex][int(count / 4)] <= float(
                                colorizer.maxLabel
                            ):  # rasterBandMinVal[bandIndex]:
                                # REMAP band values to (0,255) range
                                valRange = float(colorizer.maxLabel) - float(
                                    colorizer.minLabel
                                )  # (rasterBandMaxVal[bandIndex] - rasterBandMinVal[bandIndex])
                                colorVal = int(
                                    (
                                        rasterBandVals[bandIndex][int(count / 4)]
                                        - float(colorizer.minLabel)
                                    )
                                    / valRange
                                    * 255
                                )
                                if colorizer.invertColorRamp is True:
                                    if valRange == 0:
                                        if float(colorizer.maxLabel) == 0:
                                            colorVal = 0
                                        else:
                                            colorVal = 255
                                    else:
                                        colorVal = int(
                                            (
                                                -rasterBandVals[bandIndex][
                                                    int(count / 4)
                                                ]
                                                + float(colorizer.maxLabel)
                                            )
                                            / valRange
                                            * 255
                                        )
                                color = (colorVal << 16) + (colorVal << 8) + colorVal
                        except:  # if no Min Max labels:
                            # REMAP band values to (0,255) range
                            valRange = max(rasterBandVals[bandIndex]) - min(
                                rasterBandVals[bandIndex]
                            )  # (rasterBandMaxVal[bandIndex] - rasterBandMinVal[bandIndex])

                            if valRange == 0:
                                if min(rasterBandVals[bandIndex]) == 0:
                                    colorVal = 0
                                else:
                                    colorVal = 255
                            else:
                                colorVal = int(
                                    (
                                        rasterBandVals[bandIndex][int(count / 4)]
                                        - min(rasterBandVals[bandIndex])
                                    )
                                    / valRange
                                    * 255
                                )
                            color = (colorVal << 16) + (colorVal << 8) + colorVal
                else:  # rgb
                    # REMAP band values to (0,255) range
                    if rvalRange is not None and redBand is not None:
                        if rvalRange == 0:
                            if float(rbvalMin) == 0:
                                colorVal = 0
                            else:
                                colorVal = 255
                        else:
                            colorRVal = int(
                                (
                                    rasterBandVals[redBand][int(count / 4)]
                                    - float(rbvalMin)
                                )
                                / rvalRange
                                * 255
                            )
                    else:
                        colorRVal = 0
                    if gvalRange is not None and greenBand is not None:
                        if gvalRange == 0:
                            if float(gbvalMin) == 0:
                                colorVal = 0
                            else:
                                colorVal = 255
                        else:
                            colorGVal = int(
                                (
                                    rasterBandVals[greenBand][int(count / 4)]
                                    - float(gbvalMin)
                                )
                                / gvalRange
                                * 255
                            )
                    else:
                        colorGVal = 0
                    if bvalRange is not None and blueBand is not None:
                        if bvalRange == 0:
                            if float(bbvalMin) == 0:
                                colorVal = 0
                            else:
                                colorVal = 255
                        else:
                            colorBVal = int(
                                (
                                    rasterBandVals[blueBand][int(count / 4)]
                                    - float(bbvalMin)
                                )
                                / bvalRange
                                * 255
                            )
                    else:
                        colorBVal = 0
                    # print("__pixel color_")
                    # print(colorRVal)
                    # print(colorGVal)
                    # print(colorBVal)

                    color = (colorRVal << 16) + (colorGVal << 8) + colorBVal

                colors.extend([color, color, color, color])
                count += 4

        mesh = constructMeshFromRaster(vertices, faces, colors)

        time1 = datetime.now()
        # print(f"Time to get Raster: {(time1-time0).total_seconds()} sec")
        # after the entire loop

        if mesh is not None:
            mesh.units = dataStorage.currentUnits
            b.displayValue = [mesh]
        else:
            logToUser(
                "Something went wrong. Mesh cannot be created, only raster data will be sent. ",
                level=2,
                plugin=plugin.dockwidget,
            )

        return b

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return None


def featureToNative(
    feature: Base, fields: dict, geomType: str, sr: arcpy.SpatialReference, dataStorage
):
    print("04_____Feature To Native correct____________")
    print(feature)
    feat = {}
    try:
        try:
            speckle_geom = feature[
                "geometry"
            ]  # for created in QGIS / ArcGIS Layer type
        except:
            speckle_geom = feature  # for created in other software

        arcGisGeom = None
        if isinstance(speckle_geom, list):
            if len(speckle_geom) > 1 or geomType == "Multipoint":
                arcGisGeom = convertToNativeMulti(speckle_geom, sr, dataStorage)
            else:
                if len(speckle_geom) > 0:
                    arcGisGeom = convertToNative(speckle_geom[0], sr, dataStorage)
        else:
            arcGisGeom = convertToNative(speckle_geom, sr, dataStorage)

        if arcGisGeom is not None:
            feat.update({"arcGisGeomFromSpeckle": arcGisGeom})
        else:
            return None
        # print(arcGisGeom)
        # print(feat)
        for key, variant in fields.items():
            value = None
            try:
                value = feature[key]
            except:
                if key == "Speckle_ID":
                    try:
                        value = str(
                            feature["speckle_id"]
                        )  # if GIS already generated this field
                    except Exception as e:
                        # print(e)
                        value = str(feature["id"])
                else:
                    # print(key)
                    # arcpy.AddWarning(f'Field {key} not found')
                    try:
                        value = feature.attributes[key]
                    except:
                        try:
                            value = feature.attributes[key.replace("attributes_", "")]
                        except:
                            pass

            if variant == "TEXT":
                value = str(value)
                if len(value) > 255:
                    # print(len(value))
                    value = value[:255]
                    logToUser(
                        f'Field "{key}" values are trimmed at 255 characters',
                        level=2,
                        func=inspect.stack()[0][3],
                    )
                    # arcpy.AddWarning(
                    #    f'Field "{key}" values are trimmed at 255 characters'
                    # )
            if (
                variant == getVariantFromValue(value)
                and value != "NULL"
                and value != "None"
            ):
                feat.update({key: value})
            else:
                if variant == "TEXT":
                    feat.update({key: None})
                if variant == "FLOAT":
                    feat.update({key: None})
                if variant == "LONG":
                    feat.update({key: None})
                if variant == "SHORT":
                    feat.update({key: None})
        # print(feat)
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return feat


r"""
def featureToNative(feature: Base, fields: "QgsFields", dataStorage):
    feat = QgsFeature()
    # print("___featureToNative")
    try:
        qgsGeom = None

        if isinstance(feature, GisNonGeometryElement):
            pass
        else:
            try:
                speckle_geom = (
                    feature.geometry
                )  # for QGIS / ArcGIS Layer type from 2.14
            except:
                try:
                    speckle_geom = feature[
                        "geometry"
                    ]  # for QGIS / ArcGIS Layer type before 2.14
                except:
                    speckle_geom = feature  # for created in other software

            if not isinstance(speckle_geom, list):
                qgsGeom = convertToNative(speckle_geom, dataStorage)

            elif isinstance(speckle_geom, list):
                if len(speckle_geom) == 1:
                    qgsGeom = convertToNative(speckle_geom[0], dataStorage)
                elif len(speckle_geom) > 1:
                    qgsGeom = convertToNativeMulti(speckle_geom, dataStorage)
                else:
                    logToUser(
                        f"Feature '{feature.id}' does not contain geometry",
                        level=2,
                        func=inspect.stack()[0][3],
                    )

            if qgsGeom is not None:
                feat.setGeometry(qgsGeom)
            else:
                return None

        feat.setFields(fields)
        for field in fields:
            name = str(field.name())
            variant = field.type()
            # if name == "id": feat[name] = str(feature["applicationId"])

            try:
                value = feature.attributes[name]  # fro 2.14 onwards
            except:
                try:
                    value = feature[name]
                except:
                    if name == "Speckle_ID":
                        try:
                            value = str(
                                feature["Speckle_ID"]
                            )  # if GIS already generated this field
                        except:
                            try:
                                value = str(feature["speckle_id"])
                            except:
                                value = str(feature["id"])
                    else:
                        value = None
                        # logger.logToUser(f"Field {name} not found", Qgis.Warning)
                        # return None

            if variant == QVariant.String:
                value = str(value)

            if isinstance(value, str) and variant == QVariant.Date:  # 14
                y, m, d = value.split("(")[1].split(")")[0].split(",")[:3]
                value = QDate(int(y), int(m), int(d))
            elif isinstance(value, str) and variant == QVariant.DateTime:
                y, m, d, t1, t2 = value.split("(")[1].split(")")[0].split(",")[:5]
                value = QDateTime(int(y), int(m), int(d), int(t1), int(t2))

            if (
                variant == getVariantFromValue(value)
                and value != "NULL"
                and value != "None"
            ):
                feat[name] = value

        return feat
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return feat
"""


def bimFeatureToNative(
    feature: Base,
    fields: dict,
    sr: arcpy.SpatialReference,
    path: str,
    dataStorage,
):
    # print("04_________BIM Feature To Native____________")
    feat_updated = {}
    try:
        feat = {}
        feat.update({"arcGisGeomFromSpeckle": ""})
        # feat_updated = updateFeat(exist_feat, fields, feature)

        try:
            if "Speckle_ID" not in fields.keys() and feature["id"]:
                feat.update("Speckle_ID", "TEXT")
        except:
            pass
        feat_updated = updateFeat(feat, fields, feature)

        return feat_updated
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
    return feat_updated


def nonGeomFeatureToNative(feature: Base, fields: "QgsFields", dataStorage):
    try:
        exist_feat = QgsFeature()
        exist_feat.setFields(fields)
        feat_updated = updateFeat(exist_feat, fields, feature)
        return feat_updated

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def cadFeatureToNative(
    feature: Base, fields: dict, sr: arcpy.SpatialReference, dataStorage
):

    print("04_________CAD Feature To Native____________")
    feat = {}
    try:
        try:
            speckle_geom = feature["geometry"]  # for created in QGIS Layer type
        except:
            speckle_geom = feature  # for created in other software

        if isinstance(speckle_geom, list):
            arcGisGeom = convertToNativeMulti(speckle_geom, sr, dataStorage)
        else:
            arcGisGeom = convertToNative(speckle_geom, sr, dataStorage)

        if arcGisGeom is not None:
            feat.update({"arcGisGeomFromSpeckle": arcGisGeom})
        else:
            return

        try:
            if "Speckle_ID" not in fields.keys() and feature["id"]:
                feat.update("Speckle_ID", "TEXT")
        except:
            pass

        #### setting attributes to feature
        feat_updated = updateFeat(feat, fields, feature)
        # print(feat)
        # print(fields)
        return feat_updated

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return

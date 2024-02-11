from datetime import datetime
import json
import math
import os

from typing import Dict, Any, Callable, List, Optional, Tuple

from specklepy.objects import Base
from specklepy.objects.geometry import Mesh
import arcpy
from arcpy.management import CreateCustomGeoTransformation
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer

import inspect

from speckle.speckle.converter.geometry.conversions import (
    convertToSpeckle,
    convertToNative,
    convertToNativeMulti,
)
from speckle.speckle.converter.layers.utils import (
    findTransformation,
    getVariantFromValue,
    traverseDict,
    traverseDictByKey,
    hsv_to_rgb,
)
from speckle.speckle.converter.geometry.point import pointToSpeckle
from speckle.speckle.converter.geometry.mesh import (
    constructMeshFromRaster,
    meshToNative,
)
from speckle.speckle.converter.layers.symbology import jsonFromLayerStyle
from speckle.speckle.utils.panel_logging import logToUser
from speckle.speckle.plugin_utils.helpers import findOrCreatePath

import numpy as np
import colorsys


def featureToSpeckle(
    fieldnames,
    attr_list,
    index: int,
    f_shape,
    projectCRS: arcpy.SpatialReference,
    project: ArcGISProject,
    selectedLayer: arcLayer,
):
    print("___________Feature to Speckle____________")
    b = Base(units="m")
    try:
        data = arcpy.Describe(selectedLayer.dataSource)
        layer_sr = data.spatialReference  # if sr.type == "Projected":
        geomType = data.shapeType  # Polygon, Point, Polyline, Multipoint, MultiPatch
        featureType = (
            data.featureType
        )  # Simple,SimpleJunction,SimpleJunction,ComplexEdge,Annotation,CoverageAnnotation,Dimension,RasterCatalogItem
        print(geomType)
        # print(hasattr(data, "isRevit"))
        # print(hasattr(data, "isIFC"))
        # print(hasattr(data, "bimLevels"))
        # print(hasattr(data, "hasSpatialIndex"))
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
        print(layer_sr.name)
        print(projectCRS.name)

        ######################################### Convert geometry ##########################################
        try:
            geom = convertToSpeckle(
                f_shape, index, selectedLayer, geomType, featureType
            )
            print(geom)
            b["geometry"] = []
            if geom is not None and geom != "None":
                if isinstance(geom, List):
                    for g in geom:
                        if g is not None and g != "None":
                            b["geometry"].append(g)
                        else:
                            arcpy.AddError(f"Feature skipped due to invalid geometry")
                            print(g)
                else:
                    b["geometry"] = [geom]
            else:
                arcpy.AddError(f"Feature skipped due to invalid geometry")
                print(geom)

        except Exception as error:
            print("Error converting geometry: " + str(error))
            print(selectedLayer)
            logToUser(
                "Error converting geometry: " + str(error),
                level=2,
                func=inspect.stack()[0][3],
            )
        print(geom)
        # print(featureType)
        for i, name in enumerate(fieldnames):
            corrected = name.replace("/", "_").replace(".", "-")
            if corrected != "Shape" and corrected != "Shape@":
                # different ID behaviors: https://support.esri.com/en/technical-article/000010834
                # save all attribute, duplicate one into applicationId
                b[corrected] = attr_list[i]
                if corrected == "FID" or corrected == "OID" or corrected == "OBJECTID":
                    b["applicationId"] = str(attr_list[i])
        # print(b)
        print("______end of __Feature to Speckle____________________")
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return b


def featureToNative(
    feature: Base, fields: dict, geomType: str, sr: arcpy.SpatialReference, dataStorage
):
    print("04_____Feature To Native____________")
    feat = {}
    try:
        try:
            speckle_geom = feature[
                "geometry"
            ]  # for created in QGIS / ArcGIS Layer type
        except:
            speckle_geom = feature  # for created in other software
        # print(speckle_geom)

        arcGisGeom = None
        if isinstance(speckle_geom, list):
            if len(speckle_geom) > 0 or geomType == "Multipoint":
                arcGisGeom = convertToNativeMulti(speckle_geom, sr, dataStorage)
            else:
                arcGisGeom = convertToNative(speckle_geom[0], sr, dataStorage)
        else:
            arcGisGeom = convertToNative(speckle_geom, sr, dataStorage)

        if arcGisGeom is not None:
            feat.update({"arcGisGeomFromSpeckle": arcGisGeom})
        else:
            return None
        print(arcGisGeom)
        print(feat)
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
                        print(e)
                        value = str(feature["id"])
                else:
                    print(key)
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
                    print(len(value))
                    value = value[:255]
                    arcpy.AddWarning(
                        f'Field "{key}" values are trimmed at 255 characters'
                    )
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
        print(feat)
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return feat


def bimFeatureToNative(
    feature: Base, fields: dict, sr: arcpy.SpatialReference, path: str, dataStorage
):
    # print("04_________BIM Feature To Native____________")
    feat_updated = {}
    try:
        feat = {}
        feat.update({"arcGisGeomFromSpeckle": ""})

        try:
            if "Speckle_ID" not in fields.keys() and feature["id"]:
                feat.update("Speckle_ID", "TEXT")
        except:
            pass
        feat_updated = updateFeat(feat, fields, feature)

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return feat_updated


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
            if len(speckle_geom) > 1:
                arcGisGeom = convertToNativeMulti(speckle_geom, sr, dataStorage)
            else:
                arcGisGeom = convertToNative(speckle_geom[0], sr, dataStorage)
        else:
            arcGisGeom = convertToNative(speckle_geom, sr, dataStorage)

        if arcGisGeom is not None:
            feat.update({"arcGisGeomFromSpeckle": arcGisGeom})
        else:
            return None

        try:
            if "Speckle_ID" not in fields.keys() and feature["id"]:
                feat.update("Speckle_ID", "TEXT")
        except:
            pass

        #### setting attributes to feature
        feat_updated = updateFeat(feat, fields, feature)
        print(feat)
        print(fields)
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return feat_updated


def addFeatVariant(key, variant, value, f):
    # print("Add feat variant")
    feat = f
    try:
        if variant == "TEXT":
            value = str(value)[:255]
            if len(value) > 255:
                print(len(value))
                value = value[:255]
                arcpy.AddWarning(f'Field "{key}" values are trimmed at 255 characters')

        if value != "NULL" and value != "None":
            # if key == 'area': print(value); print(type(value)); print(getVariantFromValue(value))
            if variant == getVariantFromValue(
                value
            ):  # or (variant=="FLOAT" and isinstance(value, int)):
                feat.update({key: value})
            elif variant == "LONG" and isinstance(
                value, float
            ):  # if object has been modified
                feat.update({key: int(value)})
            elif variant == "FLOAT" and isinstance(
                value, int
            ):  # if object has been modified
                feat.update({key: float(value)})
            else:
                feat.update({key: None})
        elif (
            variant == "TEXT"
            or variant == "FLOAT"
            or variant == "LONG"
            or variant == "SHORT"
        ):
            feat.update({key: None})
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return feat


def updateFeat(feat: dict, fields: dict, feature: Base) -> Dict[str, Any]:
    # print("Update feat")
    feat_sorted = {}
    try:
        for key, variant in fields.items():
            try:
                if key == "Speckle_ID":
                    value = str(feature["id"])

                    feat[key] = value

                    feat = addFeatVariant(key, variant, value, feat)
                else:
                    try:
                        value = feature[key]
                        # if key == "area": print(feature[key]); print(type(feature[key]))
                        feat = addFeatVariant(key, variant, value, feat)
                    except:
                        value = None
                        rootName = key.split("_")[0]
                        # try: # if the root category exists
                        # if its'a list
                        if isinstance(feature[rootName], list):
                            for i in range(len(feature[rootName])):
                                try:
                                    newF, newVals = traverseDict(
                                        {},
                                        {},
                                        rootName + "_" + str(i),
                                        feature[rootName][i],
                                    )
                                    for i, (key, value) in enumerate(newVals.items()):
                                        for k, (x, y) in enumerate(newF.items()):
                                            if key == x:
                                                variant = y
                                                break
                                        feat = addFeatVariant(key, variant, value, feat)
                                except Exception as e:
                                    print(e)
                        # except: # if not a list
                        else:
                            try:
                                newF, newVals = traverseDict(
                                    {}, {}, rootName, feature[rootName]
                                )
                                for i, (key, value) in enumerate(newVals.items()):
                                    for k, (x, y) in enumerate(newF.items()):
                                        if key == x:
                                            variant = y
                                            break
                                    feat = addFeatVariant(key, variant, value, feat)
                            except Exception as e:
                                feat.update({key: None})
            except Exception as e:
                feat.update({key: None})
        feat_sorted = {k: v for k, v in sorted(feat.items(), key=lambda item: item[0])}
        # print("_________________end of updating a feature_________________________")
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return feat_sorted


def rasterFeatureToSpeckle(
    selectedLayer: arcLayer, projectCRS: arcpy.SpatialReference, project: ArcGISProject
) -> Base:
    print("_________ Raster feature to speckle______")
    b = Base(units="m")
    try:
        dataStorage = plugin.project.dataStorage
        # https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/raster-object.htm

        # get Raster object of entire raster dataset
        my_raster = arcpy.Raster(selectedLayer.dataSource)
        print(my_raster.mdinfo)  # None

        rasterBandCount = my_raster.bandCount
        rasterBandNames = my_raster.bandNames
        rasterDimensions = [my_raster.width, my_raster.height]
        if rasterDimensions[0] * rasterDimensions[1] > 1000000:
            arcpy.AddWarning("Large layer: ")

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
            geom = pointToSpeckle(reprojectedPt.getPart(), None, None, dataStorage)
            if geom != None:
                b["displayValue"] = [geom]
            print(geom)
        except Exception as error:
            logToUser(
                "Error converting point geometry: " + str(error),
                level=2,
                func=inspect.stack()[0][3],
            )

        for i, item in enumerate(rasterBandNames):
            print(item)
            rb = my_raster.getRasterBands(item)
            print(rb)
            print(np.shape(rb.read()))
            valMin = rb.minimum
            valMax = rb.maximum
            bandVals = np.swapaxes(rb.read(), 1, 2).flatten()  # .tolist() np.flip( , 0)

            bandValsFlat = []
            bandValsFlat.extend(bandVals.tolist())
            # print(bandValsFlat)

            const = float(-1 * math.pow(10, 30))
            defaultNoData = rb.noDataValue

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
            if rasterBandNoDataVal[len(rasterBandNoDataVal) - 1] is None:
                rasterBandNoDataVal[len(rasterBandNoDataVal) - 1] = "None"

            rasterBandVals.append(bandValsFlat)
            rasterBandMinVal.append(valMin)
            rasterBandMaxVal.append(valMax)

            # print(rb.getColormap()) #None

            b["@(10000)" + item + "_values"] = (
                bandValsFlat  # [0:int(max_values/rasterBandCount)]
            )

        b["X resolution"] = rasterResXY[0]
        b["Y resolution"] = -1 * rasterResXY[1]
        b["X pixels"] = rasterDimensions[0]
        b["Y pixels"] = rasterDimensions[1]
        b["Band count"] = rasterBandCount
        b["Band names"] = rasterBandNames
        b["NoDataVal"] = rasterBandNoDataVal
        # creating a mesh
        vertices = []
        faces = []
        colors = []
        count = 0

        # print(my_raster.variables)
        print(selectedLayer.symbology)  # None
        colorizer = None
        # renderer = selectedLayer.symbology.renderer
        if hasattr(selectedLayer.symbology, "colorizer"):
            colorizer = selectedLayer.symbology.colorizer

            print(
                colorizer
            )  # <arcpy._colorizer.RasterStretchColorizer object at 0x000001780497FBC8>
            print(colorizer.type)  # RasterStretchColorizer
        else:
            # RGB colorizer
            root_path = "\\".join(project.filePath.split("\\")[:-1])
            root_path: str = (
                os.path.expandvars(r"%LOCALAPPDATA%")
                + "\\Temp\\Speckle_ArcGIS_temp\\"
                + datetime.now().strftime("%Y-%m-%d %H-%M")
            )
            root_path += "\\Layers_Speckle\\raster_bands\\"
            findOrCreatePath(root_path)

            # if not os.path.exists(root_path + '\\Layers_Speckle\\raster_bands'): os.makedirs(root_path + '\\Layers_Speckle\\raster_bands')
            path_style = root_path + selectedLayer.name + "_temp.lyrx"
            symJson = jsonFromLayerStyle(selectedLayer, path_style)

            # read from Json
            # print(symJson["layerDefinitions"][0]["colorizer"])
            try:
                greenBand = symJson["layerDefinitions"][0]["colorizer"][
                    "greenBandIndex"
                ]
            except:
                greenBand = None
            try:
                blueBand = symJson["layerDefinitions"][0]["colorizer"]["blueBandIndex"]
            except:
                blueBand = None

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
                rbvalMin = min(rbVals)
                rbvalMax = max(rbVals)
                rvalRange = float(rbvalMax) - float(rbvalMin)
                print(rbvalMin)
                print(rbvalMax)
                print(rvalRange)
            except Exception as e:
                print(e)
                rvalRange = None
            try:
                gbVals = rasterBandVals[greenBand]
                gbvalMin = min(gbVals)
                gbvalMax = max(gbVals)
                gvalRange = float(gbvalMax) - float(gbvalMin)
                print(gbvalMin)
                print(gbvalMax)
                print(gvalRange)
            except:
                gvalRange = None
            try:
                bbVals = rasterBandVals[blueBand]
                bbvalMin = min(bbVals)
                bbvalMax = max(bbVals)
                bvalRange = float(bbvalMax) - float(bbvalMin)
                print(bbvalMin)
                print(bbvalMax)
                print(bvalRange)
            except:
                bvalRange = None

        rendererType = ""
        # if hasattr(selectedLayer.symbology, 'renderer'): rendererType = selectedLayer.symbology.renderer.type #e.g. SimpleRenderer
        # custom color ramp {"type": "algorithmic", "fromColor": [115, 76, 0, 255],"toColor": [255, 25, 86, 255], "algorithm": "esriHSVAlgorithm"}.
        # custom color map {'values': [0, 1, 2, 3, 4, 5], 'colors': ['#000000', '#DCFFDF', '#B8FFBE', '#85FF90', '#50FF60','#00AB10']}

        bandIndex = 0
        r"""
        if colorizer.type == "RasterStretchColorizer":
            print("___Color cell: RasterStretchColorizer___")
            print(colorizer.band)
            #colorRamps = project.listColorRamps()
            bandIndex = colorizer.band

            colorizerData = None
            colorRamp = None

            colorizerData = traverseDictByKey(layerFileContent, "colorizer", None)
            print(colorizerData) # {'type': 'CIMRasterStretchColorizer', 'resamplingType': 

            #noDataColor: List[float] = traverseDictByKey(colorizerData, "noDataColor")['values']
            colorRamp = traverseDictByKey(colorizerData, "colorRamp", None)

            colorsFromRamp: List[List[float]] = []
            colorsFromRampType = []
            try:
                for i, item in enumerate(colorRamp['colorRamps']): 
                    colorsFromRamp.append(item['fromColor']['values'])
                    colorsFromRampType.append(item['fromColor']['type'])
                    if i == len(colorRamp['colorRamps'])-1 : 
                        colorsFromRamp.append(item['toColor']['values'])
                        colorsFromRampType.append(item['toColor']['type'])
            except: pass
            print(colorsFromRamp) # [[220, 100, 45, 100], [214.12, 100, 100, 100], [201, 25, 100, 100]]
            rangesNumber = len(colorsFromRamp) - 1 # 2 (if 3 colors)

            colorsFromRampRGB = []
            for i, item in enumerate(colorsFromRamp): 
                if ("CIMHSVColor" in colorsFromRampType[i]): 
                    # https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/rasterclassbreak-class.htm
                    newR, newG, newB = colorsys.hsv_to_rgb(item[0],item[1],item[2])
                    colorsFromRampRGB.append( ( int(newR*255), int( newG*255), int(newB*255) )  )
                elif ("HSL" in colorsFromRampType[i]): 
                    # https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/rasterclassbreak-class.htm
                    newR, newG, newB = colorsys.hsl_to_rgb(item[0],item[1],item[2])
                    colorsFromRampRGB.append( ( int(newR*255), int( newG*255), int(newB*255) )  )
                else:
                    colorsFromRampRGB.append(item)

            rs = [float(x[0]) for x in colorsFromRampRGB]
            gs = [float(x[1]) for x in colorsFromRampRGB]
            bs = [float(x[2]) for x in colorsFromRampRGB]
        """
        # identify symbology type and if Multiband, which band is which color
        for v in range(rasterDimensions[1]):  # each row, Y
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
                noValColor = [
                    0,
                    0,
                    0,
                ]  # selectedLayer.renderer().nodataColor().getRgb()

                r"""
                if colorizer.type == "RasterStretchColorizer":   

                    # find position of the alue on the range
                    if rasterBandVals[bandIndex][int(count/4)] >= float(colorizer.minLabel) and rasterBandVals[bandIndex][int(count/4)] <= float(colorizer.maxLabel) : #rasterBandMinVal[bandIndex]: 
                        # REMAP band values to (0,255) range
                        valRange = float(colorizer.maxLabel) - float(colorizer.minLabel) #(rasterBandMaxVal[bandIndex] - rasterBandMinVal[bandIndex])
                        position = (rasterBandVals[bandIndex][int(count/4)] - float(colorizer.minLabel)) / valRange 
                        
                        print(position) # 0.8461538461538461
                        print("calc range")
                        localPosition = 0
                        for n in range(rangesNumber): # 0, 1
                            print(n)
                            start = n/rangesNumber
                            end = (n+1)/rangesNumber
                            if position <= end and position >= start: 
                                localRange = end-start
                                localPosition = position - start
                                break # n - is the range we need, number bentween n and (n+1)
                        print(localPosition) # 0.34615384615384615
                        print(n)

                        localColor = []
                        for c in [rs,gs,bs]: 
                            print(c)
                            # go through each color: 
                            localColor.append( int( (c[n+1] - c[n]) * localPosition + c[n] ) )
                            print(localColor)
                        color =  (localColor[0]<<16) + (localColor[1]<<8) + localColor[2]
                        print(color)


                elif colorizer.type == "RasterClassifyColorizer":
                    print(colorizer.noDataColor)
                    print(colorizer.breakCount) # number of classes 
                    print(colorizer.classBreaks)
                    print(colorizer.classificationField)
                    print(colorizer.classificationMethod)
                    print(colorizer.colorRamp)
                elif colorizer.type == "RasterUniqueValueColorizer":
                    print(colorizer.noDataColor)
                    print(colorizer.colorRamp)
                    print(colorizer.field)
                    print(colorizer.groups)
                """
                # else:
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

                        # print("__pixel color_")
                        # print(colorRVal)
                        # print(colorGVal)
                        # print(colorBVal)
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
        if b["displayValue"] is None:
            b["displayValue"] = []
        b["displayValue"].append(mesh)

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return b


r"""
    # example raster stretch colorizer

    {'type': 'CIMRasterStretchColorizer', 'resamplingType': 'NearestNeighbor', 
    'noDataColor': {'type': 'CIMRGBColor', 'values': [255, 255, 255, 0]}, 
    'backgroundColor': {'type': 'CIMRGBColor', 'values': [255, 255, 255, 0]}, 
    'colorRamp': 
    {
      'type': 'CIMMultipartColorRamp',
      'colorRamps': 
        [{
          'type': 'CIMPolarContinuousColorRamp', 
          'colorSpace': {'type': 'CIMICCColorSpace', 'url': 'Default RGB'}, 
          'fromColor': {'type': 'CIMHSVColor', 'values': [220, 100, 45, 100]}, 
          'toColor': {'type': 'CIMHSVColor', 'values': [214, 100, 100, 100]}, 
          'interpolationSpace': 'HSV', 'polarDirection': 'Counterclockwise'
          }, 
          {
            'type': 'CIMPolarContinuousColorRamp', 
            'colorSpace': {'type': 'CIMICCColorSpace', 'url': 'Default RGB'}, 
            'fromColor': {'type': 'CIMHSVColor', 'values': [214.12, 100, 100, 100]}, 
            'toColor': {'type': 'CIMHSVColor', 'values': [201, 25, 100, 100]}, 
            'interpolationSpace': 'HSV', 'polarDirection': 'Counterclockwise'
          }], 
          'weights': [1, 1]}, 
    'colorScheme': 'Bathymetry #3', 'customStretchMax': 1, 'gammaValue': 1, 'hillshadeZFactor': 1, 
    'maxPercent': 2, 'minPercent': 2, 'standardDeviationParam': 2, 'statsType': 'Dataset', 
    'stretchClasses': [
      {'type': 'CIMRasterStretchClass', 'label': '3', 'value': 3}, 
      {'type': 'CIMRasterStretchClass', 'value': 22.5}, 
      {'type': 'CIMRasterStretchClass', 'label': '42', 'value': 42}
      ], 
      'stretchStats': {'type': 'StatsHistogram', 'min': 3, 'max': 42, 'mean': 21.761538461538, 'stddev': 11.387670241563, 'resolution': 0.15294117647058825}, 
      'stretchType': 'StandardDeviations'}
    """

"""
Contains all Layer related classes and methods.
"""

import enum
import hashlib
import inspect
import math
import random
from typing import List, Tuple, Union

import os
import time
from datetime import datetime
import inspect

import numpy as np

import arcgisscripting
import arcpy

from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from arcpy.management import (
    CreateTable,
    CreateFeatureclass,
    MakeFeatureLayer,
    AddFields,
    AlterField,
    DefineProjection,
)
from specklepy.logging.exceptions import SpeckleInvalidUnitException


from specklepy.objects import Base
from specklepy.objects.geometry import (
    Mesh,
    Point,
    Line,
    Curve,
    Circle,
    Ellipse,
    Polycurve,
    Arc,
    Polyline,
)

from specklepy.objects.GIS.CRS import CRS
from specklepy.objects.GIS.layers import VectorLayer, RasterLayer, Layer
from specklepy.objects.other import Collection
from specklepy.objects.GIS.geometry import GisPolygonElement, GisNonGeometryElement
from specklepy.objects.units import get_units_from_string


from speckle.speckle.plugin_utils.helpers import (
    findFeatColors,
    findOrCreatePath,
    jsonFromList,
    removeSpecialCharacters,
    validateNewFclassName,
    removeSpecialCharacters,
    SYMBOL,
    UNSUPPORTED_PROVIDERS,
)

from speckle.speckle.converter.geometry.mesh import writeMeshToShp
from speckle.speckle.converter.geometry.point import (
    pointToNative,
    pointToNativeWithoutTransforms,
)
from speckle.speckle.converter.features.feature_conversions import (
    featureToSpeckle,
    rasterFeatureToSpeckle,
    featureToNative,
    nonGeomFeatureToNative,
    cadFeatureToNative,
    bimFeatureToNative,
)
from speckle.speckle.converter.layers.utils import (
    collectionsFromJson,
    colorFromSpeckle,
    colorFromSpeckle,
    generate_qgis_app_id,
    generate_qgis_raster_app_id,
    getDisplayValueList,
    getLayerGeomType,
    getLayerAttributes,
    tryCreateGroupTree,
    trySaveCRS,
    validateAttributeName,
    newLayerGroupAndName,
    validate_path,
)

from speckle.speckle.converter.layers.symbology import (
    vectorRendererToNative,
    rasterRendererToNative,
    rendererToSpeckle,
    cadBimRendererToNative,
)

from speckle.speckle.utils.panel_logging import logToUser
from speckle.speckle.utils.project_vars import (
    findOrCreateTableField,
    findOrCreateRow,
    findOrCreateRowInFeatureTable,
)

GEOM_LINE_TYPES = [
    "Objects.Geometry.Line",
    "Objects.Geometry.Polyline",
    "Objects.Geometry.Curve",
    "Objects.Geometry.Arc",
    "Objects.Geometry.Circle",
    "Objects.Geometry.Ellipse",
    "Objects.Geometry.Polycurve",
]


def convertSelectedLayersToSpeckle(
    baseCollection: Collection,
    layers: List,
    tree_structure: List[str],
    projectCRS,
    plugin,
) -> List[Union[VectorLayer, RasterLayer]]:
    """Converts the current selected layers to Speckle"""
    dataStorage = plugin.dataStorage
    result = []
    try:
        project = plugin.project

        ## Generate dictionnary from the list of layers to send
        jsonTree = {}
        for i, layer in enumerate(layers):
            # print("Tree structure: ")
            # print(tree_structure)
            structure = tree_structure[i]

            if structure.startswith(SYMBOL):
                structure = structure[len(SYMBOL) :]

            levels = structure.split(SYMBOL)
            while "" in levels:
                levels.remove("")

            jsonTree = jsonFromList(jsonTree, levels)

        for i, layer in enumerate(layers):
            logToUser(
                f"Converting layer '{layer.name}'...",
                level=0,
                plugin=plugin.dockwidget,
            )

            converted = layerToSpeckle(layer, projectCRS, plugin)
            # print(converted)
            if converted is not None:
                # print(tree_structure)
                structure = tree_structure[i]
                if structure.startswith(SYMBOL):
                    structure = structure[len(SYMBOL) :]
                levels = structure.split(SYMBOL)
                while "" in levels:
                    levels.remove("")

                baseCollection = collectionsFromJson(
                    jsonTree, levels, converted, baseCollection
                )
            else:
                logToUser(
                    f"Layer '{layer.name}' conversion failed",
                    level=2,
                    plugin=plugin.dockwidget,
                )

        return baseCollection
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return baseCollection


def layerToSpeckle(
    selectedLayer: arcLayer,
    projectCRS,
    plugin,
) -> Union[
    VectorLayer, RasterLayer
]:  # now the input is QgsVectorLayer instead of qgis._core.QgsLayerTreeLayer
    """Converts a given QGIS Layer to Speckle"""
    speckleLayer = None
    try:
        # print("___layerToSpeckle")
        dataStorage = plugin.dataStorage
        dataStorage.latestActionFeaturesReport = []
        project: ArcGISProject = plugin.project

        try:
            data = arcpy.Describe(selectedLayer.dataSource)
        except OSError as e:
            logToUser(str(e.args[0]), level=2, func=inspect.stack()[0][3])
            return

        layerName = selectedLayer.name
        crs = data.SpatialReference
        units = str(project.activeMap.spatialReference.linearUnitName)
        layerObjs = []

        offset_x = plugin.dataStorage.crs_offset_x
        offset_y = plugin.dataStorage.crs_offset_y
        rotation = plugin.dataStorage.crs_rotation

        units_proj = plugin.dataStorage.currentUnits
        units_layer_native = str(crs.linearUnitName)  # "m"
        units_layer = units_layer_native

        if crs.type == "Geographic":
            units_layer = "m"  ## specklepy.logging.exceptions.SpeckleException: SpeckleException: Could not understand what unit degrees is referring to. Please enter a valid unit (eg ['mm', 'cm', 'm', 'in', 'ft', 'yd', 'mi']).
        if "unknown" in units_layer:
            units_layer = "m"  # if no-geometry layer
        layerObjs = []

        # Convert CRS to speckle, use the projectCRS
        speckleReprojectedCrs = CRS(
            authority_id=str(projectCRS.factoryCode),
            name=str(projectCRS.name),
            wkt=projectCRS.exportToString(),
            units=units_proj,
            offset_x=offset_x,
            offset_y=offset_y,
            rotation=rotation,
        )
        layerCRS = CRS(
            authority_id=str(crs.factoryCode),
            name=str(crs.name),
            wkt=crs.exportToString(),
            units=units_layer,
            units_native=units_layer_native,
            offset_x=offset_x,
            offset_y=offset_y,
            rotation=rotation,
        )

        if selectedLayer.isFeatureLayer:
            print("VECTOR LAYER HERE")
            print(projectCRS.exportToString())

            speckleLayer = VectorLayer(units="m")
            speckleLayer.collectionType = "VectorLayer"
            speckleLayer.name = layerName
            speckleLayer.crs = speckleReprojectedCrs
            speckleLayer.renderer = rendererToSpeckle(
                project, project.activeMap, selectedLayer, None
            )

            try:  # https://pro.arcgis.com/en/pro-app/2.8/arcpy/get-started/the-spatial-reference-object.htm

                # print(data.datasetType) # FeatureClass
                if (
                    data.datasetType == "FeatureClass"
                ):  # FeatureClass, ?Table Properties, ?Datasets

                    # write feature attributes
                    fieldnames = [field.name for field in data.fields]
                    rows_shapes = arcpy.da.SearchCursor(
                        selectedLayer.dataSource, "Shape@"
                    )  # arcpy.da.SearchCursor(in_table, field_names, {where_clause}, {spatial_reference}, {explode_to_points}, {sql_clause})
                    # print("__ start iterating features")
                    row_shapes_list = [x for k, x in enumerate(rows_shapes)]
                    for i, features in enumerate(row_shapes_list):

                        print(
                            "____error Feature # " + str(i + 1)
                        )  # + " / " + str(sum(1 for _ in enumerate(rows_shapes))))
                        if features[0] is None:
                            continue
                        feat = features[0]
                        # print(feat) # <geoprocessing describe geometry object object at 0x000002A75D6A4BD0>
                        # print(feat.hasCurves)
                        # print(feat.partCount)

                        if feat is not None:
                            print(
                                feat
                            )  # <geoprocessing describe geometry object object at 0x0000026796C47780>
                            rows_attributes = arcpy.da.SearchCursor(
                                selectedLayer.dataSource, fieldnames
                            )
                            row_attr = []
                            for k, attrs in enumerate(rows_attributes):
                                if i == k:
                                    row_attr = attrs
                                    break

                            # if curves detected, createa new feature class, turn to segments and get the same feature but in straigt lines
                            # print(feat.hasCurves)
                            if feat.hasCurves:
                                # f_class_modified = curvedFeatureClassToSegments(layer)
                                # rows_shapes_modified = arcpy.da.SearchCursor(f_class_modified, "Shape@")
                                # row_shapes_list_modified = [x for k, x in enumerate(rows_shapes_modified)]

                                feat = feat.densify("ANGLE", 1000, 0.12)
                                # print(feat)

                            all_errors_count = 0
                            dataStorage.latestActionFeaturesReport.append(
                                {"feature_id": str(i + 1), "obj_type": "", "errors": ""}
                            )
                            b = featureToSpeckle(
                                fieldnames,
                                row_attr,
                                i,
                                feat,
                                projectCRS,
                                selectedLayer,
                                plugin,
                            )
                            if b is not None:
                                layerObjs.append(b)
                                # print(b)

                            if (
                                dataStorage.latestActionFeaturesReport[
                                    len(dataStorage.latestActionFeaturesReport) - 1
                                ]["errors"]
                                != ""
                            ):
                                all_errors_count += 1
                        else:
                            logToUser(
                                "Feature skipped due to invalid geometry",
                                level=2,
                                func=inspect.stack()[0][3],
                            )

                        # print("____End of Feature # " + str(i + 1))

                    # print("__ finish iterating features")
                    speckleLayer.elements = layerObjs
                    speckleLayer.geomType = data.shapeType

                    if len(speckleLayer.elements) == 0:
                        return None

                    # layerBase.renderer = layerRenderer
                    # layerBase.applicationId = selectedLayer.id()

                if all_errors_count == 0:
                    dataStorage.latestActionReport.append(
                        {
                            "feature_id": layerName,
                            "obj_type": speckleLayer.speckle_type,
                            "errors": "",
                        }
                    )
                else:
                    dataStorage.latestActionReport.append(
                        {
                            "feature_id": layerName,
                            "obj_type": speckleLayer.speckle_type,
                            "errors": f"{all_errors_count} features failed",
                        }
                    )
                for item in dataStorage.latestActionFeaturesReport:
                    dataStorage.latestActionReport.append(item)

            except OSError as e:
                logToUser(str(e), level=2, func=inspect.stack()[0][3])
                return None

        elif selectedLayer.isRasterLayer:
            print("RASTER HERE")
            # print(selectedLayer.name)  # London_square.tif
            # print(
            #    arcpy.Describe(selectedLayer.dataSource)
            # )  # <geoprocessing describe data object object at 0x000002507C7F3BB0>
            # print(arcpy.Describe(selectedLayer.dataSource).datasetType)  # RasterDataset
            b = rasterFeatureToSpeckle(selectedLayer, projectCRS, plugin)

            if b is None:
                dataStorage.latestActionReport.append(
                    {
                        "feature_id": layerName,
                        "obj_type": "Raster Layer",
                        "errors": "Layer failed to send",
                    }
                )
                return None

            layerObjs.append(b)

            # Convert layer to speckle
            speckleLayer = RasterLayer(
                units=units_proj,
                name=layerName,
                crs=speckleReprojectedCrs,
                rasterCrs=layerCRS,
                elements=layerObjs,
            )

            dataStorage.latestActionReport.append(
                {
                    "feature_id": layerName,
                    "obj_type": speckleLayer.speckle_type,
                    "errors": "",
                }
            )
            speckleLayer.renderer = rendererToSpeckle(
                project, project.activeMap, selectedLayer, b
            )

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        dataStorage.latestActionReport.append(
            {
                "feature_id": layerName,
                "obj_type": "",
                "errors": f"Layer conversion failed: {e}",
            }
        )
        return None
    return speckleLayer


def layerToNative(
    layer: Union[Layer, VectorLayer, RasterLayer],
    streamBranch: str,
    nameBase: str,
    plugin,
):
    try:
        project = plugin.project
        # plugin.dataStorage.currentCRS = project.crs()

        if isinstance(layer.collectionType, str) and layer.collectionType.endswith(
            "VectorLayer"
        ):
            vectorLayerToNative(layer, streamBranch, nameBase, plugin)
            return
        elif isinstance(layer.collectionType, str) and layer.collectionType.endswith(
            "RasterLayer"
        ):
            rasterLayerToNative(layer, streamBranch, nameBase, plugin)
            return
        # if collectionType exists but not defined
        elif isinstance(layer.type, str) and layer.type.endswith(
            "VectorLayer"
        ):  # older commits
            vectorLayerToNative(layer, streamBranch, nameBase, plugin)
            return
        elif isinstance(layer.type, str) and layer.type.endswith(
            "RasterLayer"
        ):  # older commits
            rasterLayerToNative(layer, streamBranch, nameBase, plugin)
            return
    except:
        try:
            if isinstance(layer.type, str) and layer.type.endswith(
                "VectorLayer"
            ):  # older commits
                vectorLayerToNative(layer, streamBranch, nameBase, plugin)
                return
            elif isinstance(layer.type, str) and layer.type.endswith(
                "RasterLayer"
            ):  # older commits
                rasterLayerToNative(layer, streamBranch, nameBase, plugin)
                return

            return
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def nonGeometryLayerToNative(
    geomList: List[Base], nameBase: str, val_id: str, streamBranch: str, plugin
):
    # print("01_____NON-GEOMETRY layer to native")

    try:
        layerName = removeSpecialCharacters(nameBase)
        newFields = getLayerAttributes(geomList)

        if plugin.dataStorage.latestHostApp.endswith("excel"):
            plugin.dockwidget.signal_6.emit(
                {
                    "plugin": plugin,
                    "layerName": layerName,
                    "val_id": val_id,
                    "streamBranch": streamBranch,
                    "newFields": newFields,
                    "geomList": geomList,
                }
            )
        else:
            plugin.dockwidget.signal_5.emit(
                {
                    "plugin": plugin,
                    "layerName": layerName,
                    "layer_id": val_id,
                    "streamBranch": streamBranch,
                    "newFields": newFields,
                    "geomList": geomList,
                }
            )

        return

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def addExcelMainThread(obj: Tuple):
    # print("___addExcelMainThread")
    try:
        finalName = ""
        plugin = obj["plugin"]
        layerName = obj["layerName"]
        streamBranch = obj["streamBranch"]
        val_id = obj["val_id"]
        newFields = obj["newFields"]
        geomList = obj["geomList"]
        plugin.dockwidget.msgLog.removeBtnUrl("cancel")

        dataStorage = plugin.dataStorage
        project: QgsProject = plugin.dataStorage.project

        geomType = "None"
        geom_print = "Table"

        shortName = layerName.split(SYMBOL)[len(layerName.split(SYMBOL)) - 1][:50]
        try:
            layerName = layerName.split(shortName)[0] + shortName + ("_" + geom_print)
        except:
            layerName = layerName + ("_" + geom_print)
        finalName = shortName + ("_" + geom_print)

        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName
        layerGroup = tryCreateGroupTree(project.layerTreeRoot(), groupName, plugin)

        dataStorage.latestActionLayers.append(finalName)

        ###########################################

        # get features and attributes
        fets = []
        report_features = []
        all_feature_errors_count = 0
        # print("before newFields")
        # print(newFields)
        for f in geomList:
            # print(f)
            # pre-fill report:
            report_features.append(
                {"speckle_id": f.id, "obj_type": f.speckle_type, "errors": ""}
            )

            new_feat = nonGeomFeatureToNative(f, newFields, plugin.dataStorage)
            if new_feat is not None and new_feat != "":
                fets.append(new_feat)
            else:
                logToUser(
                    f"Table feature skipped due to invalid data",
                    level=2,
                    func=inspect.stack()[0][3],
                )
                report_features[len(report_features) - 1].update(
                    {"errors": "Table feature skipped due to invalid data"}
                )
                all_feature_errors_count += 1

        if newFields is None:
            newFields = QgsFields()

        # print("04")
        vl = None
        vl = QgsVectorLayer(
            geomType + "?crs=" + "WGS84", finalName, "memory"
        )  # do something to distinguish: stream_id_latest_name
        project.addMapLayer(vl, False)
        pr = vl.dataProvider()
        vl.startEditing()

        # add Layer attribute fields
        pr.addAttributes(newFields.toList())
        vl.updateFields()

        pr.addFeatures(fets)
        vl.updateExtents()
        vl.commitChanges()

        # print("07")
        layerGroup.addLayer(vl)

        # report
        all_feature_errors_count = 0
        for item in report_features:
            if item["errors"] != "":
                all_feature_errors_count += 1

        # print("11")
        obj_type = "Vector Layer"
        if all_feature_errors_count == 0:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{val_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": "",
                }
            )
        else:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{val_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": f"{all_feature_errors_count} features failed",
                }
            )

        # print("12")
        for item in report_features:
            dataStorage.latestActionReport.append(item)
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        # report
        obj_type = "Vector Layer"
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{val_id} {finalName}",
                "obj_type": obj_type,
                "errors": f"{e}",
            }
        )
        dataStorage.latestConversionTime = datetime.now()


def addNonGeometryMainThread(obj: Tuple):
    # print("___addCadMainThread")
    try:
        finalName = ""
        plugin = obj["plugin"]
        layerName = obj["layerName"]
        layer_id = obj["layer_id"]
        streamBranch = obj["streamBranch"]
        newFields = obj["newFields"]
        geomList = obj["geomList"]
        plugin.dockwidget.msgLog.removeBtnUrl("cancel")

        project = plugin.dataStorage.project
        dataStorage = plugin.dataStorage

        geomType = "None"
        geom_print = "Table"

        shortName = layerName.split(SYMBOL)[len(layerName.split(SYMBOL)) - 1][:50]
        try:
            layerName = layerName.split(shortName)[0] + shortName + ("_" + geom_print)
        except:
            layerName = layerName + ("_" + geom_print)
        finalName = shortName + ("_" + geom_print)

        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName
        layerGroup = tryCreateGroupTree(project.layerTreeRoot(), groupName, plugin)

        dataStorage.latestActionLayers.append(finalName)

        crs = project.crs()  # QgsCoordinateReferenceSystem.fromWkt(layer.crs.wkt)
        plugin.dataStorage.currentUnits = str(QgsUnitTypes.encodeUnit(crs.mapUnits()))
        if (
            plugin.dataStorage.currentUnits is None
            or plugin.dataStorage.currentUnits == "degrees"
        ):
            plugin.dataStorage.currentUnits = "m"
        # authid = trySaveCRS(crs, streamBranch)

        if crs.isGeographic is True:
            logToUser(
                f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly",
                level=1,
                func=inspect.stack()[0][3],
            )

        vl = QgsVectorLayer(
            geomType + "?crs=" + crs.authid(), finalName, "memory"
        )  # do something to distinguish: stream_id_latest_name
        vl.setCrs(crs)
        project.addMapLayer(vl, False)

        pr = vl.dataProvider()
        vl.startEditing()

        # create list of Features (fets) and list of Layer fields (fields)
        attrs = QgsFields()
        fets = []
        fetIds = []
        fetColors = []

        report_features = []
        all_feature_errors_count = 0
        for f in geomList[:]:
            # pre-fill report:
            report_features.append(
                {"speckle_id": f.id, "obj_type": f.speckle_type, "errors": ""}
            )

            new_feat = nonGeomFeatureToNative(f, newFields, plugin.dataStorage)
            # update attrs for the next feature (if more fields were added from previous feature)

            # print("________cad feature to add")
            if new_feat is not None and new_feat != "":
                fets.append(new_feat)
                for a in newFields.toList():
                    attrs.append(a)

                pr.addAttributes(
                    newFields
                )  # add new attributes from the current object
                fetIds.append(f.id)
                fetColors = findFeatColors(fetColors, f)
            else:
                logToUser(
                    f"Table feature skipped due to invalid data",
                    level=2,
                    func=inspect.stack()[0][3],
                )
                report_features[len(report_features) - 1].update(
                    {"errors": "Table feature skipped due to invalid data"}
                )
                all_feature_errors_count += 1

        # add Layer attribute fields
        pr.addAttributes(newFields)
        vl.updateFields()

        # pr = vl.dataProvider()
        pr.addFeatures(fets)
        vl.updateExtents()
        vl.commitChanges()

        layerGroup.addLayer(vl)

        # report
        obj_type = (
            geom_print + " Vector Layer"
            if "Mesh" not in geom_print
            else "Multipolygon Vector Layer"
        )
        if all_feature_errors_count == 0:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": "",
                }
            )
        else:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer_id} {finalName}",
                    "obj_type": obj_type,
                    "errors": f"{all_feature_errors_count} features failed",
                }
            )
        for item in report_features:
            dataStorage.latestActionReport.append(item)
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        # report
        obj_type = geom_print + "Vector Layer"
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{layer_id} {finalName}",
                "obj_type": obj_type,
                "errors": f"{e}",
            }
        )
        dataStorage.latestConversionTime = datetime.now()


def geometryLayerToNative(
    layerContentList: List[Base],
    layerName: str,
    val_id: str,
    streamBranch: str,
    plugin,
    matrix=None,
):
    print(f"01_____GEOMETRY layer to native: {layerName}")
    try:
        # print(layerContentList)
        geom_meshes = []

        geom_points = []
        geom_polylines = []

        layer_points = None
        layer_polylines = None
        # geom_meshes = []
        val = None

        # filter speckle objects by type within each layer, create sub-layer for each type (points, lines, polygons, mesh?)
        for geom in layerContentList:
            # print(geom)
            if isinstance(geom, Point):
                geom_points.append(geom)
                continue
            elif (
                isinstance(geom, Line)
                or isinstance(geom, Polyline)
                or isinstance(geom, Curve)
                or isinstance(geom, Arc)
                or isinstance(geom, Circle)
                or isinstance(geom, Ellipse)
                or isinstance(geom, Polycurve)
            ):
                geom_polylines.append(geom)
                continue
            try:
                if (
                    geom.speckle_type.endswith(".ModelCurve")
                    and geom["baseCurve"].speckle_type in GEOM_LINE_TYPES
                ):
                    geom_polylines.append(geom["baseCurve"])
                    continue
                elif geom["baseLine"].speckle_type in GEOM_LINE_TYPES:
                    geom_polylines.append(geom["baseLine"])
                    # don't skip the rest if baseLine is found
            except Exception as e:
                print(e)
                pass  # check for the Meshes

            # ________________get list of display values for Meshes___________________________
            val = getDisplayValueList(geom)
            # print(val) # List of Meshes

            if isinstance(val, List) and len(val) > 0 and isinstance(val[0], Mesh):
                # print("__________GET ACTUAL ELEMENT BEFORE DISPLAY VALUE")
                # print(val[0]) # Mesh

                if isinstance(geom, List):
                    geom_meshes.extend(geom)
                else:
                    geom_meshes.append(geom)
            # print("__GEOM MESHES")
            # print(geom_meshes)

        if len(geom_meshes) > 0:
            bimVectorLayerToNative(
                geom_meshes,
                layerName,
                val_id,
                "Mesh",
                streamBranch.replace(SYMBOL + SYMBOL, SYMBOL).replace(
                    SYMBOL + SYMBOL, SYMBOL
                ),
                plugin,
                matrix,
            )
        if len(geom_points) > 0:
            cadVectorLayerToNative(
                geom_points,
                layerName,
                val_id,
                "Point",
                streamBranch.replace(SYMBOL + SYMBOL, SYMBOL).replace(
                    SYMBOL + SYMBOL, SYMBOL
                ),
                plugin,
                matrix,
            )
        if len(geom_polylines) > 0:
            cadVectorLayerToNative(
                geom_polylines,
                layerName,
                val_id,
                "Polyline",
                streamBranch.replace(SYMBOL + SYMBOL, SYMBOL).replace(
                    SYMBOL + SYMBOL, SYMBOL
                ),
                plugin,
                matrix,
            )

        return True

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def bimVectorLayerToNative(
    geomList: List[Base],
    layerName_old: str,
    val_id: str,
    geomType: str,
    streamBranch: str,
    plugin,
    matrix: list = None,
):
    print("02_________BIM vector layer to native_____")
    try:
        project = plugin.project
        active_map = project.activeMap

        layerName = layerName_old  # [:50]
        layerName = removeSpecialCharacters(layerName)

        newFields = getLayerAttributes(geomList)

        plugin.dockwidget.signal_2.emit(
            {
                "plugin": plugin,
                "geomType": "Multipatch",
                "layerName": layerName,
                "layer_id": val_id,
                "streamBranch": streamBranch,
                "newFields": newFields,
                "geomList": geomList,
                "matrix": matrix,
            }
        )

        return
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def addBimMainThread(obj: Tuple):
    try:
        finalName = ""
        plugin = obj["plugin"]
        geomType = obj["geomType"]
        layerName = obj["layerName"]
        layer_id = obj["layer_id"]
        streamBranch = obj["streamBranch"]
        newFields = obj["newFields"]
        geomList = obj["geomList"]
        matrix = obj["matrix"]
        plugin.dockwidget.msgLog.removeBtnUrl("cancel")

        dataStorage = plugin.dataStorage
        dataStorage.matrix = matrix
        project = dataStorage.project
        active_map = project.activeMap
        geom_print = "Mesh"
        report_features = []

        layerName = removeSpecialCharacters(layerName)
        layerName = layerName + "_" + geomType
        # print(layerName)

        shortName = layerName.split(SYMBOL)[len(layerName.split(SYMBOL)) - 1][:50]
        try:
            layerName = (
                layerName.split(shortName)[0] + shortName + ("_as_" + geom_print)
            )
        except:
            layerName = layerName + ("_as_" + geom_print)
        finalName = shortName + ("_as_" + geom_print)
        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName

        dataStorage.latestActionLayers.append(finalName)

        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName

        layerGroup = None
        newGroupName = groupName  # f"{streamBranch}"
        # print(newGroupName)
        layerGroup = tryCreateGroupTree(project, groupName, plugin)

        # find ID of the layer with a matching name in the "latest" group
        newName = (
            f'{newGroupName.split("_")[len(newGroupName.split("_"))-1]}_{layerName}'
        )
        newName = newName.split(SYMBOL)[-1]
        all_layer_names = []
        for l in project.activeMap.listLayers():
            if l.longName.startswith(newGroupName + "\\"):
                all_layer_names.append(l.shortName)
        # print(all_layer_names)

        longName = newGroupName + "\\" + newName
        newName = validateNewFclassName(
            newName, all_layer_names
        )  # , newGroupName + "\\")

        # newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'
        # newName_shp = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}/{finalName[:30]}'
        newName_shp = newName + "_shp"

        # get Project CRS, use it by default for the new received layer
        sr = project.activeMap.spatialReference
        if sr.type == "Geographic":
            logToUser(
                f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly",
                level=1,
                func=inspect.stack()[0][3],
            )

        units = str(sr.linearUnitName)
        dataStorage.currentUnits = units
        if dataStorage.currentUnits is None or dataStorage.currentUnits == "degrees":
            dataStorage.currentUnits = "m"

        p = (
            os.path.expandvars(r"%LOCALAPPDATA%")
            + "\\Temp\\Speckle_QGIS_temp\\"
            + datetime.now().strftime("%Y-%m-%d_%H-%M")
        )
        findOrCreatePath(p)
        path = p
        # logToUser(f"BIM layers can only be received in an existing saved project. Layer {layerName} will be ignored", level = 1, func = inspect.stack()[0][3])

        path_bim = (
            path
            + "/Layers_Speckle/BIM_layers/"
            + streamBranch
            + "/"
            + layerName[:30]
            + "/"
        )  # arcpy.env.workspace + "\\" #

        findOrCreatePath(path_bim)
        # print(path_bim)
        class_name = "f_class_" + newName

        shp = writeMeshToShp(geomList, path_bim + newName_shp, dataStorage)
        dataStorage.matrix = None
        if shp is None:
            return
        # print("____ meshes saved___")

        cursor = arcpy.da.SearchCursor(shp, "Speckle_ID")
        class_shapes = [shp_id[0] for n, shp_id in enumerate(cursor)]
        del cursor

        validated_class_path = validate_path(class_name, plugin)
        # print(validated_class_path)
        validated_class_name = validated_class_path.split("\\")[
            len(validated_class_path.split("\\")) - 1
        ]

        all_classes = arcpy.ListFeatureClasses()
        validated_class_name = validateNewFclassName(validated_class_name, all_classes)
        # print(validated_class_name)
        # print(validated_class_name)

        path = plugin.workspace  # project.filePath.replace("aprx","gdb") #

        f_class = arcpy.conversion.FeatureClassToFeatureClass(
            shp, path, validated_class_name
        )
        arcpy.management.DefineProjection(f_class, sr.exportToString())

        # get and set Layer attribute fields
        # example: https://resource.esriuk.com/blog/an-introductory-slice-of-arcpy-in-arcgis-pro/
        fields_to_ignore = ["arcgisgeomfromspeckle", "shape", "objectid", "displayMesh"]
        matrix = []
        matrix_no_id = []
        all_keys = []
        all_key_types = []
        max_len = 52

        # print("___ after layer attributes: ___________")
        for key, value in newFields.items():
            existingFields = [fl.name for fl in arcpy.ListFields(validated_class_name)]
            # print(existingFields)
            if (
                key not in existingFields and key.lower() not in fields_to_ignore
            ):  # exclude geometry and default existing fields
                # print(key)
                # signs that should not be used as field names and table names: https://support.esri.com/en/technical-article/000005588
                key = (
                    key.replace(" ", "_")
                    .replace("-", "_")
                    .replace("(", "_")
                    .replace(")", "_")
                    .replace(":", "_")
                    .replace("\\", "_")
                    .replace("/", "_")
                    .replace('"', "_")
                    .replace("&", "_")
                    .replace("@", "_")
                    .replace("$", "_")
                    .replace("%", "_")
                    .replace("^", "_")
                )
                if key[0] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                    key = "_" + key
                if len(key) > max_len:
                    key = key[:max_len]
                # print(all_keys)
                if key in all_keys:
                    for index, letter in enumerate(
                        "1234567890abcdefghijklmnopqrstuvwxyz"
                    ):
                        if len(key) < max_len and (key + letter) not in all_keys:
                            key += letter
                            break
                        if len(key) == max_len and (key[:9] + letter) not in all_keys:
                            key = key[:9] + letter
                            break
                if key not in all_keys:
                    all_keys.append(key)
                    all_key_types.append(value)
                    # print(all_keys)
                    if key.lower() == "speckle_id":
                        matrix.append(["Speckle_ID", value, "Speckle_ID", 255])
                    else:
                        matrix.append([key, value, key, 255])
                        matrix_no_id.append([key, value, key, 255])
        # 51.5019052°N  0.1076614°W 51.5020862°N  51.5019596,-0.1077379
        # print(len(all_keys))
        # print(matrix)
        try:
            if len(matrix) > 0:
                AddFields(str(f_class), matrix_no_id)
        except Exception as e:
            print(e)
        # print(matrix)

        fets = []
        fetIds = []
        fetColors = []
        rows_delete = []

        cursor = arcpy.da.SearchCursor(f_class, "Speckle_ID")
        class_shapes = [shp_id[0] for n, shp_id in enumerate(cursor)]
        del cursor

        # print(len(class_shapes))
        # print(len(geomList))

        # print("_________BIM FeatureS To Native___________")
        report_features = []
        all_feature_errors_count = 0
        for f in geomList[:]:
            try:
                # pre-fill report:
                report_features.append(
                    {"speckle_id": f.id, "obj_type": f.speckle_type, "errors": ""}
                )
                exist_feat = None
                shape_id = None
                n = None
                for n, shape_id in enumerate(class_shapes):
                    # print(shape_id[0])
                    if shape_id == f.id:
                        exist_feat = f
                        break

                if exist_feat is None:
                    logToUser(
                        f"Feature skipped due to invalid geometry",
                        level=2,
                        func=inspect.stack()[0][3],
                    )
                    report_features[len(report_features) - 1].update(
                        {"errors": "Feature skipped due to invalid geometry"}
                    )
                    all_feature_errors_count += 1
                    rows_delete.append(n)
                    continue

                new_feat = bimFeatureToNative(
                    exist_feat, newFields, sr, path_bim, dataStorage
                )
                if new_feat is not None and new_feat != "":
                    fetColors = findFeatColors(fetColors, f)

                    fets.append(new_feat)
                    fetIds.append(f.id)
                    # print(len(fets))
                else:
                    logToUser(
                        f"Feature skipped due to invalid geometry",
                        level=2,
                        func=inspect.stack()[0][3],
                    )
                    report_features[len(report_features) - 1].update(
                        {"errors": "Feature skipped due to invalid geometry"}
                    )
                    all_feature_errors_count += 1
                    rows_delete.append(n)

            except Exception as e:
                print(e)

        # print(rows_delete)
        cursor = arcpy.da.UpdateCursor(f_class, "Speckle_ID")
        for n, row in enumerate(cursor):
            if n in rows_delete:
                cursor.deleteRow()
        del cursor
        # print(n)

        if len(fets) == 0:
            return None
        count = 0
        rowValues = []
        for i, feat in enumerate(fets):

            row = []
            heads = []
            for key in all_keys:
                try:
                    row.append(feat[key])
                    heads.append(key)
                except Exception as e:
                    row.append(None)
                    heads.append(key)

            rowValues.append(row)
            count += 1
        # print(heads)
        # print(len(heads))

        if len(heads) > 0:
            with arcpy.da.UpdateCursor(f_class, heads) as cur:
                # For each row, evaluate the WELL_YIELD value (index position
                # of 0), and update WELL_CLASS (index position of 1)
                shp_num = 0
                try:
                    for rowShape in cur:
                        for i, r in enumerate(rowShape):
                            rowShape[i] = rowValues[shp_num][i]
                            if matrix[i][1] == "TEXT" and rowShape[i] is not None:
                                rowShape[i] = str(rowValues[shp_num][i])
                            if isinstance(
                                rowValues[shp_num][i], str
                            ):  # cut if string is too long
                                rowShape[i] = rowValues[shp_num][i][:255]
                        cur.updateRow(rowShape)
                        shp_num += 1
                except Exception as e:
                    # print("Layer attr error: " + str(e))
                    # print(shp_num)
                    # print(len(rowValues))
                    logToUser(
                        "Layer attribute error: " + e,
                        level=2,
                        func=inspect.stack()[0][3],
                    )
            del cur

        # print("create layer:")
        vl = MakeFeatureLayer(
            str(f_class), "x" + str(random.randint(100000, 500000))
        ).getOutput(0)
        vl.name = newName

        active_map.addLayerToGroup(layerGroup, vl)
        # print("created2")

        vl2 = None
        newGroupName = newGroupName.replace(SYMBOL + SYMBOL, SYMBOL).replace(
            SYMBOL + SYMBOL, SYMBOL
        )
        # print(newGroupName.replace(SYMBOL, "\\") + newName)
        for l in project.activeMap.listLayers():
            # print(l.longName)
            if l.longName == newGroupName.replace(SYMBOL, "\\") + newName:
                vl2 = l
                # print(l.longName)
                break
        # print(vl2)

        path_lyr = cadBimRendererToNative(
            project, active_map, layerGroup, fetColors, vl2, f_class, heads
        )

        # report
        obj_type = "Multipatch Layer"
        if all_feature_errors_count == 0:
            dataStorage.latestActionReport.append(
                {
                    "layer_name": f"{layerName}",
                    "obj_type": obj_type,
                    "errors": "",
                }
            )
        else:
            dataStorage.latestActionReport.append(
                {
                    "layer_name": f"{layerName}",
                    "obj_type": obj_type,
                    "errors": f"{all_feature_errors_count} features failed",
                }
            )
        for item in report_features:
            dataStorage.latestActionReport.append(item)
        dataStorage.latestConversionTime = datetime.now()

        return vl2

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        # report
        obj_type = "Multipatch Layer"
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{layer_id} {finalName}",
                "obj_type": obj_type,
                "errors": f"{e}",
            }
        )
        dataStorage.latestConversionTime = datetime.now()


def cadVectorLayerToNative(
    geomList: List[Base],
    layerName: str,
    val_id: str,
    geomType: str,
    streamBranch: str,
    plugin,
    matrix=None,
):
    print("_______cadVectorLayerToNative__")
    try:
        plugin.dockwidget.signal_3.emit(
            {
                "plugin": plugin,
                "geomType": geomType,
                "layerName": layerName,
                "layer_id": val_id,
                "streamBranch": streamBranch,
                "geomList": geomList,
                "matrix": matrix,
            }
        )

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        return


def addCadMainThread(obj: Tuple):
    print("___addCadMainThread")
    try:

        plugin = obj["plugin"]
        geomType = obj["geomType"]
        layerName = obj["layerName"]
        val_id = obj["layer_id"]
        streamBranch = obj["streamBranch"]
        geomList = obj["geomList"]
        matrix = obj["matrix"]

        project = plugin.project
        dataStorage = plugin.dataStorage
        dataStorage.matrix = matrix

        # get Project CRS, use it by default for the new received layer
        layerName = removeSpecialCharacters(layerName)
        layerName = layerName + "_" + geomType
        # print(layerName)

        shortName = layerName.split(SYMBOL)[len(layerName.split(SYMBOL)) - 1][:50]
        geom_print = geomType
        try:
            layerName = (
                layerName.split(shortName)[0] + shortName + ("_as_" + geom_print)
            )
        except:
            layerName = layerName + ("_as_" + geom_print)
        finalName = shortName + ("_as_" + geom_print)
        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName

        dataStorage.latestActionLayers.append(finalName)

        # map data
        active_map = project.activeMap
        # print(active_map.spatialReference)
        sr = arcpy.SpatialReference(text=active_map.spatialReference.exportToString())
        path = (
            plugin.workspace
        )  # project.filePath.replace("aprx","gdb") #"\\".join(project.filePath.split("\\")[:-1]) + "\\speckle_layers\\" #arcpy.env.workspace + "\\" #

        units = str(sr.linearUnitName)  # <Units.m: 'm'>
        try:
            units = get_units_from_string(units)
        except SpeckleInvalidUnitException:
            units = "none"

        if units is None or units in ["degrees", "none"]:
            units = "m"
        plugin.dataStorage.currentUnits = units

        if sr.type == "Geographic":
            logToUser(
                f"Project CRS is set to Geographic type, and objects in linear units might not be received correctly",
                level=1,
                func=inspect.stack()[0][3],
                plugin=plugin.dockwidget,
            )

        layerGroup = None
        newGroupName = groupName  # f"{streamBranch}"
        # print(newGroupName)
        layerGroup = tryCreateGroupTree(project, groupName, plugin)

        # find ID of the layer with a matching name in the "latest" group
        newName = (
            f'{newGroupName.split("_")[len(newGroupName.split("_"))-1]}_{layerName}'
        )
        newName = newName.split(SYMBOL)[-1]
        all_layer_names = []
        for l in project.activeMap.listLayers():
            if l.longName.startswith(newGroupName + "\\"):
                all_layer_names.append(l.shortName)
        # print(all_layer_names)

        longName = newGroupName + "\\" + newName
        newName = validateNewFclassName(
            newName, all_layer_names
        )  # , newGroupName + "\\")

        # print(geomType)
        class_name = "f_class_" + newName
        all_classes = arcpy.ListFeatureClasses()
        class_name = validateNewFclassName(class_name, all_classes)
        f_class = CreateFeatureclass(
            path, class_name, geomType, has_z="ENABLED", spatial_reference=sr
        )
        # print(f_class)
        arcpy.management.DefineProjection(f_class, sr)

        newFields = getLayerAttributes(geomList)

        fields_to_ignore = ["arcgisgeomfromspeckle", "shape", "objectid"]
        matrix = []
        all_keys = []
        all_key_types = []
        max_len = 52
        for key, value in newFields.items():
            existingFields = [fl.name for fl in arcpy.ListFields(class_name)]
            if (
                key not in existingFields and key.lower() not in fields_to_ignore
            ):  # exclude geometry and default existing fields
                # signs that should not be used as field names and table names: https://support.esri.com/en/technical-article/000005588
                key = (
                    key.replace(" ", "_")
                    .replace("-", "_")
                    .replace("(", "_")
                    .replace(")", "_")
                    .replace(":", "_")
                    .replace("\\", "_")
                    .replace("/", "_")
                    .replace('"', "_")
                    .replace("&", "_")
                    .replace("@", "_")
                    .replace("$", "_")
                    .replace("%", "_")
                    .replace("^", "_")
                )
                if key[0] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                    key = "_" + key
                if len(key) > max_len:
                    key = key[:max_len]
                # print(all_keys)
                if key in all_keys:
                    for index, letter in enumerate(
                        "1234567890abcdefghijklmnopqrstuvwxyz"
                    ):
                        if len(key) < max_len and (key + letter) not in all_keys:
                            key += letter
                            break
                        if len(key) == max_len and (key[:9] + letter) not in all_keys:
                            key = key[:9] + letter
                            break
                if key not in all_keys:
                    all_keys.append(key)
                    all_key_types.append(value)
                    # print(all_keys)
                    matrix.append([key, value, key, 255])
                    # print(matrix)
        if len(matrix) > 0:
            AddFields(str(f_class), matrix)

        fets = []
        fetColors = []
        report_features = []
        all_feature_errors_count = 0
        for f in geomList[:]:
            # pre-fill report:
            report_features.append(
                {"speckle_id": f.id, "obj_type": f.speckle_type, "errors": ""}
            )
            new_feat = cadFeatureToNative(f, newFields, sr, dataStorage)
            if new_feat != "" and new_feat != None:
                fetColors = findFeatColors(fetColors, f)
                fets.append(new_feat)
            else:
                logToUser(
                    f"Feature skipped due to invalid geometry",
                    level=2,
                    func=inspect.stack()[0][3],
                )
                report_features[len(report_features) - 1].update(
                    {"errors": "Feature skipped due to invalid geometry"}
                )
                all_feature_errors_count += 1

        dataStorage.matrix = None

        # print("features created")
        # print(len(fets))
        # print(all_keys)

        if len(fets) == 0:
            return None
        count = 0
        rowValues = []
        for feat in fets:
            try:
                feat["applicationId"]
            except:
                feat.update({"applicationId": count})

            row = [feat["arcGisGeomFromSpeckle"], feat["applicationId"]]
            heads = ["Shape@", "OBJECTID"]

            for key, value in feat.items():
                # print(key, str(value))
                if key in all_keys and key.lower() not in fields_to_ignore:
                    heads.append(key)
                    row.append(value)
            rowValues.append(row)
            count += 1
        cur = arcpy.da.InsertCursor(str(f_class), tuple(heads))
        # print(heads)
        for row in rowValues:
            try:
                # print(row)
                cur.insertRow(tuple(row))
            except Exception as e:
                print(e)
        del cur
        # vl = MakeFeatureLayer(str(f_class), newName).getOutput(0)
        vl = MakeFeatureLayer(
            str(f_class), "x" + str(random.randint(100000, 500000))
        ).getOutput(0)
        vl.name = newName

        # adding layers from code solved: https://gis.stackexchange.com/questions/344343/arcpy-makefeaturelayer-management-function-not-creating-feature-layer-in-arcgis
        # active_map.addLayer(new_layer)

        active_map.addLayerToGroup(layerGroup, vl)
        # print("Layer created")

        vl2 = None
        # print(newName)
        newGroupName = newGroupName.replace(SYMBOL + SYMBOL, SYMBOL).replace(
            SYMBOL + SYMBOL, SYMBOL
        )
        # print(newGroupName.replace(SYMBOL, "\\") + newName)
        for l in project.activeMap.listLayers():
            # print(l.longName)
            if l.longName == newGroupName.replace(SYMBOL, "\\") + newName:
                vl2 = l
                break
        # print(vl2)

        path_lyr = cadBimRendererToNative(
            project, active_map, layerGroup, fetColors, vl2, f_class, heads
        )

        # report
        obj_type = (
            geom_print + " Vector Layer"
            if "Mesh" not in geom_print
            else "Multipolygon Vector Layer"
        )
        if all_feature_errors_count == 0:
            dataStorage.latestActionReport.append(
                {
                    "layer_name": f"{layerName}",
                    "obj_type": obj_type,
                    "errors": "",
                }
            )
        else:
            dataStorage.latestActionReport.append(
                {
                    "layer_name": f"{layerName}",
                    "obj_type": obj_type,
                    "errors": f"{all_feature_errors_count} features failed",
                }
            )
        for item in report_features:
            dataStorage.latestActionReport.append(item)
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        try:
            # report
            obj_type = geom_print + "Vector Layer"
            dataStorage.latestActionReport.append(
                {
                    "layer_name": f"{layerName}",
                    "obj_type": obj_type,
                    "errors": f"{e}",
                }
            )
            dataStorage.latestConversionTime = datetime.now()
        except Exception as e:
            pass


def vectorLayerToNative(
    layer: Layer or VectorLayer, streamBranch: str, nameBase: str, plugin
):
    try:
        print("_________Vector Layer to Native correct_________")

        objectEmit = {
            "layer": layer,
            "streamBranch": streamBranch,
            "nameBase": nameBase,
            "plugin": plugin,
        }
        plugin.dockwidget.signal_1.emit(objectEmit)

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])


def addVectorMainThread(obj: Tuple):
    try:
        layer = obj["layer"]
        streamBranch = obj["streamBranch"]
        nameBase = obj["nameBase"]
        plugin = obj["plugin"]
        dataStorage = plugin.dataStorage

        # particularly if the layer comes from ArcGIS
        geomType = (
            layer.geomType
        )  # for ArcGIS: Point | Multipoint | Polygon | Polyline | Multipatch
        if geomType == "None":
            addTableMainThread(obj)
            return

        geom_print = geomType

        vl = None
        project: ArcGISProject = plugin.project

        layer_elements = layer.elements
        if layer_elements is None or len(layer_elements) == 0:
            layer_elements = layer.features
        # print(layer.elements)
        # print(layer.features)
        sr = arcpy.SpatialReference(text=layer.crs.wkt)
        active_map = project.activeMap
        path = (
            plugin.workspace
        )  # project.filePath.replace("aprx","gdb") #"\\".join(project.filePath.split("\\")[:-1]) + "\\speckle_layers\\" #arcpy.env.workspace + "\\" #
        # if not os.path.exists(path): os.makedirs(path)
        # print(path)

        newName = removeSpecialCharacters(
            nameBase + SYMBOL + layer.name
        )  # + "_Speckle"
        if "." in newName:
            newName = ".".join(newName.split(".")[:-1])

        shortName = newName.split(SYMBOL)[len(newName.split(SYMBOL)) - 1][:50]
        # print(f"Final short name: {shortName}")
        try:
            layerName = newName.split(shortName)[0] + shortName  # + ("_" + geom_print)
        except:
            layerName = newName
        finalName = shortName
        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName

        layerGroup = None
        newGroupName = groupName  # f"{streamBranch}"
        # print(newGroupName)
        layerGroup = tryCreateGroupTree(project, groupName, plugin)

        # find ID of the layer with a matching name in the "latest" group
        newName = (
            f'{newGroupName.split("_")[len(newGroupName.split("_"))-1]}_{layerName}'
        )
        newName = newName.split(SYMBOL)[-1]

        dataStorage.latestActionLayers.append(finalName)

        all_layer_names = []
        for l in project.activeMap.listLayers():
            if l.longName.startswith(newGroupName + "\\"):
                all_layer_names.append(l.shortName)

        longName = newGroupName + "\\" + newName
        newName = validateNewFclassName(
            newName, all_layer_names
        )  # , newGroupName + "\\")

        # newName, layerGroup = newLayerGroupAndName(layerName, streamBranch, project)

        # print(geomType)
        if "polygon" in geomType.lower():
            geomType = "Polygon"
        if "line" in geomType.lower() or "curve" in geomType.lower():
            geomType = "Polyline"
        if "multipoint" in geomType.lower():
            geomType = "Multipoint"
        elif "point" in geomType.lower():
            geomType = "Point"
        # print(geomType)

        # print(newName)
        # path = r"C:\Users\username\Documents\ArcGIS\Projects\MyProject-test\MyProject-test.gdb\\"
        # https://community.esri.com/t5/arcgis-pro-questions/is-it-possible-to-create-a-new-group-layer-with/td-p/1068607
        # print(project.filePath.replace("aprx","gdb"))
        # print("_________create feature class___________________________________")
        # should be created inside the workspace to be a proper Feature class (not .shp) with Nullable Fields
        class_name = "f_class_" + newName
        all_classes = arcpy.ListFeatureClasses()
        class_name = validateNewFclassName(class_name, all_classes)
        # print(class_name)
        try:
            f_class = CreateFeatureclass(
                path, class_name, geomType, has_z="ENABLED", spatial_reference=sr
            )
        except arcgisscripting.ExecuteError as e:
            # print(e)
            all_classes = arcpy.ListFeatureClasses()
            class_name = validateNewFclassName(class_name, all_classes)
            f_class = CreateFeatureclass(
                path, class_name, geomType, has_z="ENABLED", spatial_reference=sr
            )

        # get and set Layer attribute fields
        # example: https://resource.esriuk.com/blog/an-introductory-slice-of-arcpy-in-arcgis-pro/
        newFields = getLayerAttributes(layer_elements)

        # print(newFields)
        fields_to_ignore = [
            "arcgisgeomfromspeckle",
            "arcGisGeomFromSpeckle",
            "shape",
            "objectid",
            "OBJECTID",
        ]
        matrix = []
        all_keys = []
        all_key_types = []
        max_len = 52
        for key, value in newFields.items():
            existingFields = [fl.name for fl in arcpy.ListFields(class_name)]
            if (
                key not in existingFields and key.lower() not in fields_to_ignore
            ):  # exclude geometry and default existing fields
                # signs that should not be used as field names and table names: https://support.esri.com/en/technical-article/000005588
                key = (
                    key.replace(" ", "_")
                    .replace("-", "_")
                    .replace("(", "_")
                    .replace(")", "_")
                    .replace(":", "_")
                    .replace("\\", "_")
                    .replace("/", "_")
                    .replace('"', "_")
                    .replace("&", "_")
                    .replace("@", "_")
                    .replace("$", "_")
                    .replace("%", "_")
                    .replace("^", "_")
                )
                if key[0] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                    key = "_" + key
                if len(key) > max_len:
                    key = key[:max_len]
                # print(all_keys)
                if key in all_keys:
                    for index, letter in enumerate(
                        "1234567890abcdefghijklmnopqrstuvwxyz"
                    ):
                        if len(key) < max_len and (key + letter) not in all_keys:
                            key += letter
                            break
                        if len(key) == max_len and (key[:9] + letter) not in all_keys:
                            key = key[:9] + letter
                            break
                if key not in all_keys:
                    all_keys.append(key)
                    all_key_types.append(value)
                    # print(all_keys)
                    matrix.append([key, value, key, 255])
                    # print(matrix)
        if len(matrix) > 0:
            AddFields(str(f_class), matrix)

        # print(layer_elements)
        fets = []
        report_features = []
        all_feature_errors_count = 0
        for f in layer_elements:
            # pre-fill report:
            report_features.append(
                {"speckle_id": f.id, "obj_type": f.speckle_type, "errors": ""}
            )
            new_feat = featureToNative(f, newFields, geomType, sr, plugin.dataStorage)
            if new_feat != "" and new_feat != None:
                fets.append(new_feat)
            else:
                logToUser(
                    f"'{geomType}' feature skipped due to invalid data",
                    level=2,
                    func=inspect.stack()[0][3],
                )
                report_features[len(report_features) - 1].update(
                    {"errors": f"'{geomType}' feature skipped due to invalid data"}
                )
                all_feature_errors_count += 1

        # print(fets)
        if len(fets) == 0:
            return None
        count = 0
        rowValues = []
        heads = None
        for feat in fets:
            # print(feat)
            try:
                feat["applicationId"]
            except:
                feat.update({"applicationId": count})

            row = [feat["arcGisGeomFromSpeckle"], feat["applicationId"]]
            heads = ["Shape@", "OBJECTID"]

            for key, value in feat.items():
                if key in all_keys and key.lower() not in fields_to_ignore:
                    heads.append(key)
                    row.append(value)
            rowValues.append(row)
            count += 1
            # print(heads)
            # print(row)
        cur = arcpy.da.InsertCursor(str(f_class), tuple(heads))
        for row in rowValues:
            # print(tuple(heads))
            # print(tuple(row))
            cur.insertRow(tuple(row))
        del cur

        # vl = MakeFeatureLayer(str(f_class), newName).getOutput(0)
        vl = MakeFeatureLayer(
            str(f_class), "x" + str(random.randint(100000, 500000))
        ).getOutput(0)
        vl.name = newName
        # print(vl)

        # adding layers from code solved: https://gis.stackexchange.com/questions/344343/arcpy-makefeaturelayer-management-function-not-creating-feature-layer-in-arcgis

        try:
            active_map.addLayerToGroup(layerGroup, vl)
        except Exception as e:
            logToUser("Layer not added: " + str(e), level=2, func=inspect.stack()[0][3])

        vl2 = None
        # print(newName)
        newGroupName = newGroupName.replace(SYMBOL + SYMBOL, SYMBOL).replace(
            SYMBOL + SYMBOL, SYMBOL
        )
        # print(newGroupName.replace(SYMBOL, "\\") + newName)
        for l in project.activeMap.listLayers():
            # print(l.longName)
            if l.longName == newGroupName.replace(SYMBOL, "\\") + newName:
                vl2 = l
                break

        path_lyr = vectorRendererToNative(
            project, active_map, layerGroup, layer, vl2, f_class, heads
        )
        # if path_lyr is not None:
        #    active_map.removeLayer(path_lyr)

        # report
        all_feature_errors_count = 0
        for item in report_features:
            if item["errors"] != "":
                all_feature_errors_count += 1

        obj_type = "Vector Layer"
        if all_feature_errors_count == 0:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer.id} {layerName}",
                    "obj_type": obj_type,
                    "errors": "",
                }
            )
        else:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer.id} {layerName}",
                    "obj_type": obj_type,
                    "errors": f"{all_feature_errors_count} features failed",
                }
            )

        for item in report_features:
            dataStorage.latestActionReport.append(item)
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
    return vl


def addTableMainThread(obj: Tuple) -> Union[str, None]:
    try:
        layer = obj["layer"]
        streamBranch = obj["streamBranch"]
        nameBase = obj["nameBase"]
        plugin = obj["plugin"]
        dataStorage = plugin.dataStorage

        vl = None
        project: ArcGISProject = plugin.project
        layerName = removeSpecialCharacters(layer.name)

        layer_elements = layer.elements
        if layer_elements is None or len(layer_elements) == 0:
            layer_elements = layer.features

        report_features = []
        all_feature_errors_count = 0
        for f in layer.elements:
            # pre-fill report:
            report_features.append(
                {"speckle_id": f.id, "obj_type": f.speckle_type, "errors": ""}
            )
        # print(layerName)
        sr = arcpy.SpatialReference(text=layer.crs.wkt)  # (text=layer.crs.wkt)
        active_map = project.activeMap
        path = (
            plugin.workspace
        )  # project.filePath.replace("aprx","gdb") #"\\".join(project.filePath.split("\\")[:-1]) + "\\speckle_layers\\" #arcpy.env.workspace + "\\" #

        # newName, layerGroup = newLayerGroupAndName(layerName, streamBranch, project)
        newFields = getLayerAttributes(layer_elements)

        newName = removeSpecialCharacters(
            nameBase + SYMBOL + layer.name
        )  # + "_Speckle"

        shortName = newName.split(SYMBOL)[len(newName.split(SYMBOL)) - 1][:50]
        # print(f"Final short name: {shortName}")
        try:
            layerName = newName.split(shortName)[0] + shortName  # + ("_" + geom_print)
        except:
            layerName = newName
        finalName = shortName
        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName

        layerGroup = None
        newGroupName = groupName  # f"{streamBranch}"
        # print(newGroupName)
        layerGroup = tryCreateGroupTree(project, groupName, plugin)

        # find ID of the layer with a matching name in the "latest" group
        newName = (
            f'{newGroupName.split("_")[len(newGroupName.split("_"))-1]}_{layerName}'
        )
        newName = newName.split(SYMBOL)[-1]

        all_classes = arcpy.ListFeatureClasses()
        class_name = f"table_{streamBranch.split(SYMBOL)[0]}_" + validateNewFclassName(
            newName, all_classes
        )
        # print(class_name)
        dataStorage.latestActionLayers.append(class_name)

        keys = list(newFields.keys())
        fields = [
            key.replace(" ", "_") for key in keys
        ]  # spaces will be replaced to underscore anyway
        table_path = path + "\\" + class_name
        table = None

        # print(fields)

        if newName not in arcpy.ListTables():
            try:
                table = CreateTable(path, class_name)
                for field in fields:
                    arcpy.management.AddField(table, field, "TEXT")
                r"""
                cursor = arcpy.da.InsertCursor(
                    table, [key.replace(" ", "_") for key in fields]
                )
                cursor.insertRow(["" for _ in range(len(fields))])
                del cursor
                """

            except Exception as e:
                logToUser(
                    "Error creating a table: " + str(e),
                    level=1,
                    func=inspect.stack()[0][3],
                )
                raise e
        else:
            for item in arcpy.ListTables():
                if item == class_name:
                    table = item
                    # print(table)
                    break
        if table is None:
            logToUser(
                f"Error creating a table '{class_name}'",
                level=1,
                func=inspect.stack()[0][3],
            )
            return
        # make sure fields exist
        for field in fields:
            findOrCreateTableField(table_path, field)

        # delete existing rows:
        with arcpy.da.UpdateCursor(table_path, fields) as cursor:
            for row in cursor:
                cursor.deleteRow()
        del cursor

        # put feature attr values to a list
        all_values = []
        for feature in layer_elements:
            feature_vals = []
            for key in keys:
                try:
                    if key == "Speckle_ID":
                        feature_vals.append(feature["id"])
                    else:
                        feature_vals.append(feature[key])
                except:
                    feature_vals.append(feature["attributes"][key])
            all_values.append(feature_vals)

        # add from scratch
        cursor = arcpy.da.InsertCursor(table_path, fields)
        for i, feature in enumerate(layer_elements):
            cursor.insertRow([v for v in all_values[i]])
        del cursor

        try:
            # print(table)
            active_map.addTableToGroup(layerGroup, table)
        except Exception as e:
            logToUser("Layer not added: " + str(e), level=2, func=inspect.stack()[0][3])

        logToUser(
            f"Table {newName} created in a Database {path}",
            level=0,
            func=inspect.stack()[0][3],
            plugin=plugin.dockwidget,
        )

        # report
        all_feature_errors_count = 0
        for item in report_features:
            if item["errors"] != "":
                all_feature_errors_count += 1

        obj_type = "Vector Layer"
        if all_feature_errors_count == 0:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer.id} {finalName}",
                    "obj_type": obj_type,
                    "errors": "",
                }
            )
        else:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer.id} {finalName}",
                    "obj_type": obj_type,
                    "errors": f"{all_feature_errors_count} features failed",
                }
            )

        for item in report_features:
            dataStorage.latestActionReport.append(item)
        dataStorage.latestConversionTime = datetime.now()

        return table

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)


def rasterLayerToNative(layer: RasterLayer, streamBranch: str, nameBase: str, plugin):
    try:
        plugin.dockwidget.signal_4.emit(
            {
                "layer": layer,
                "streamBranch": streamBranch,
                "nameBase": nameBase,
                "plugin": plugin,
            }
        )
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)


def addRasterMainThread(obj: Tuple):
    rasterLayer = None
    try:

        layer = obj["layer"]
        streamBranch = obj["streamBranch"]
        nameBase = obj["nameBase"]
        plugin = obj["plugin"]

        project = plugin.dataStorage.project
        dataStorage = plugin.dataStorage
        path = plugin.workspace

        active_map = project.activeMap
        sr = arcpy.SpatialReference(text=layer.crs.wkt)

        # newName, layerGroup = newLayerGroupAndName(layer.name, streamBranch, project)
        # newName = layer.name

        newName = removeSpecialCharacters(nameBase + SYMBOL + layer.name) + "_Speckle"
        if "." in newName:
            newName = ".".join(newName.split(".")[:-1])

        shortName = newName.split(SYMBOL)[len(newName.split(SYMBOL)) - 1][:50]
        # print(f"Final short name: {shortName}")
        try:
            layerName = newName.split(shortName)[0] + shortName  # + ("_" + geom_print)
        except:
            layerName = newName
        finalName = shortName
        try:
            groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        except:
            groupName = streamBranch + SYMBOL + layerName

        layerGroup = None
        newGroupName = groupName  # f"{streamBranch}"
        # print(newGroupName)
        layerGroup = tryCreateGroupTree(project, groupName, plugin)

        # find ID of the layer with a matching name in the "latest" group
        newName = (
            f'{newGroupName.split("_")[len(newGroupName.split("_"))-1]}_{layerName}'
        )
        newName = newName.split(SYMBOL)[-1]

        ###
        plugin.dataStorage.currentUnits = layer.crs.units
        if (
            plugin.dataStorage.currentUnits is None
            or plugin.dataStorage.currentUnits == "degrees"
        ):
            plugin.dataStorage.currentUnits = "m"

        try:
            plugin.dataStorage.current_layer_crs_offset_x = layer.crs.offset_x
            plugin.dataStorage.current_layer_crs_offset_y = layer.crs.offset_y
            plugin.dataStorage.current_layer_crs_rotation = layer.crs.rotation
        except AttributeError as e:
            print(e)
        # report on receive:

        layerName = removeSpecialCharacters(layer.name)
        shortName = newName.split(SYMBOL)[len(newName.split(SYMBOL)) - 1][:50]
        
        try:
            layerName = newName.split(shortName)[0] + shortName + "_Speckle"
        except:
            layerName = newName + "_Speckle"
        finalName = shortName + "_Speckle"

        dataStorage.latestActionLayers.append(finalName)

        rasterHasSr = False

        p: str = (
            os.path.expandvars(r"%LOCALAPPDATA%")
            + "\\Temp\\Speckle_ArcGIS_temp\\"
            + datetime.now().strftime("%Y-%m-%d_%H-%M")
        )
        # findOrCreatePath(p)
        path_bands = p + "\\Layers_Speckle\\raster_bands\\" + streamBranch
        findOrCreatePath(path_bands)

        try:
            srRasterWkt = str(layer.rasterCrs.wkt)
            srRaster = arcpy.SpatialReference(text=srRasterWkt)  # by native raster SR
            rasterHasSr = True
        except:
            srRasterWkt = str(layer.crs.wkt)
            srRaster: arcpy.SpatialReference = sr  # by layer

        layer_elements = layer.elements
        if layer_elements is None or len(layer_elements) == 0:
            layer_elements = layer.features

        feat = layer_elements[0]
        try:
            bandNames = feat["Band names"]
            bandValues = [feat["@(10000)" + name + "_values"] for name in bandNames]

            xsize = int(feat["X pixels"])
            ysize = int(feat["Y pixels"])
            xres = float(feat["X resolution"])
            yres = float(feat["Y resolution"])
            bandsCount = int(feat["Band count"])
            noDataVals = feat["NoDataVal"]
        except:
            bandNames = feat.band_names
            bandValues = [feat["@(10000)" + name + "_values"] for name in bandNames]

            xsize = int(feat.x_size)
            ysize = int(feat.y_size)
            xres = float(feat.x_resolution)
            yres = float(feat.y_resolution)
            bandsCount = int(feat.band_count)
            noDataVals = feat.noDataValue

        try:
            originPt = arcpy.Point(feat.x_origin, feat.y_origin, 0)
        except:
            originPt = arcpy.Point(
                feat["displayValue"][0].x, feat["displayValue"][0].y, 0
            )

        # if source projection is different from layer display projection, convert display OriginPt to raster source projection
        if rasterHasSr is True and srRaster.exportToString() != sr.exportToString():
            arc_pt = arcpy.PointGeometry(originPt, sr, has_z=True)
            originPt = arc_pt.projectAs(srRaster).getPart()

        bandDatasets = ""
        rastersToMerge = []
        rasterPathsToMerge = []

        # arcpy.env.overwriteOutput = True
        # https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/composite-bands.htm

        for i in range(bandsCount):
            rasterbandPath = (
                path_bands + "\\" + newName + "_Band_" + str(i + 1) + ".tif"
            )
            bandDatasets += rasterbandPath + ";"
            rasterband = np.array(bandValues[i])
            rasterband = np.reshape(rasterband, (ysize, xsize))
            leftLowerCorner = arcpy.Point(
                originPt.X, originPt.Y + (ysize * yres), originPt.Z
            )
            # # Convert array to a geodatabase raster, add to layers
            try:
                myRaster = arcpy.NumPyArrayToRaster(
                    rasterband,
                    leftLowerCorner,
                    abs(xres),
                    abs(yres),
                    noDataVals[i],
                )
            except Exception as e:
                myRaster = arcpy.NumPyArrayToRaster(
                    rasterband, leftLowerCorner, abs(xres), abs(yres)
                )

            rasterbandPath = validate_path(
                rasterbandPath, plugin
            )  # solved file saving issue
            myRaster.save(rasterbandPath)

            rastersToMerge.append(myRaster)
            rasterPathsToMerge.append(rasterbandPath)

        # mergedRaster.setProperty("spatialReference", crsRaster)
        full_path: str = validate_path(
            newName[:5] + layer.id[:8], plugin
        )  # solved file saving issue

        # mergedRaster = arcpy.ia.Merge(rastersToMerge) # glues all bands together
        # mergedRaster.save(full_path) # similar errors: https://community.esri.com/t5/python-questions/error-010240-could-not-save-raster-dataset/td-p/321690

        try:
            arcpy.management.CompositeBands(rasterPathsToMerge, full_path)
        except:  # if already exists
            full_path = full_path[:-3] + str(random.randint(100, 999))
            arcpy.management.CompositeBands(rasterPathsToMerge, full_path)

        arcpy.management.DefineProjection(full_path, srRaster)

        #print("RASTER full PATH")
        #print(full_path)
        #print(newName)
        #print(arcpy.env.workspace)

        rasterLayer = arcpy.management.MakeRasterLayer(
            full_path, "x" + str(random.randint(100000, 500000))
        ).getOutput(0)
        rasterLayer.name = finalName
        active_map.addLayerToGroup(layerGroup, rasterLayer)

        rl2 = None
        newGroupName = newGroupName.replace(SYMBOL + SYMBOL, SYMBOL).replace(
            SYMBOL + SYMBOL, SYMBOL
        )
        for l in project.activeMap.listLayers():
            if l.longName == newGroupName.replace(SYMBOL, "\\") + finalName:
                rl2 = l
                break
        rasterLayer = rasterRendererToNative(
            project, active_map, layerGroup, layer, rl2, rasterPathsToMerge, finalName
        )

        try:
            os.remove(path_bands)
        except:
            pass

        # report on receive:
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{layer.id} {finalName}",
                "obj_type": "Raster Layer",
                "errors": "",
            }
        )
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        # report on receive:
        try:
            dataStorage.latestActionReport.append(
                {
                    "speckle_id": f"{layer.id} {layer.name}",
                    "obj_type": "Raster Layer",
                    "errors": f"Receiving layer {layer.name} failed",
                }
            )
            dataStorage.latestConversionTime = datetime.now()
        except Exception as e:
            pass

    return rasterLayer

    r"""
        shortName = newName.split(SYMBOL)[len(newName.split(SYMBOL)) - 1][:50]
        # print(f"Final short name: {shortName}")
        try:
            layerName = newName.split(shortName)[0] + shortName  # + ("_" + geom_print)
        except:
            layerName = newName
        finalName = shortName  # + ("_" + geom_print)


        ######################## testing, only for receiving layers #################
        source_folder = project.absolutePath()
        feat = layer.elements[0]

        vl = None
        crs = QgsCoordinateReferenceSystem.fromWkt(
            layer.crs.wkt
        )  # moved up, because CRS of existing layer needs to be rewritten
        # try, in case of older version "rasterCrs" will not exist
        try:
            if layer.rasterCrs.wkt is None or layer.rasterCrs.wkt == "":
                raise Exception
            crsRasterWkt = str(layer.rasterCrs.wkt)
            crsRaster = QgsCoordinateReferenceSystem.fromWkt(
                layer.rasterCrs.wkt
            )  # moved up, because CRS of existing layer needs to be rewritten
        except:
            crsRasterWkt = str(layer.crs.wkt)
            crsRaster = crs
            logToUser(
                f"Raster layer '{layer.name}' might have been sent from the older version of plugin. Try sending it again for more accurate results.",
                level=1,
                plugin=plugin.dockwidget,
            )

        srsid = trySaveCRS(crsRaster, streamBranch)
        crs_new = QgsCoordinateReferenceSystem.fromSrsId(srsid)
        authid = crs_new.authid()

        try:
            bandNames = feat.band_names
        except:
            bandNames = feat["Band names"]
        bandValues = [feat["@(10000)" + name + "_values"] for name in bandNames]

        if source_folder == "":
            p = (
                os.path.expandvars(r"%LOCALAPPDATA%")
                + "\\Temp\\Speckle_QGIS_temp\\"
                + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            )
            findOrCreatePath(p)
            source_folder = p
            logToUser(
                f'Project directory not found. Raster layers will be saved to "{p}".',
                level=1,
                plugin=plugin.dockwidget,
            )

        path_fn = source_folder + "/Layers_Speckle/raster_layers/" + streamBranch + "/"
        if not os.path.exists(path_fn):
            os.makedirs(path_fn)

        fn = path_fn + layerName + ".tif"  # arcpy.env.workspace + "\\" #
        # fn = source_folder + '/' + newName.replace("/","_") + '.tif' #'_received_raster.tif'
        driver = gdal.GetDriverByName("GTiff")
        # create raster dataset
        try:
            ds = driver.Create(
                fn,
                xsize=feat.x_size,
                ysize=feat.y_size,
                bands=feat.band_count,
                eType=gdal.GDT_Float32,
            )
        except:
            ds = driver.Create(
                fn,
                xsize=feat["X pixels"],
                ysize=feat["Y pixels"],
                bands=feat["Band count"],
                eType=gdal.GDT_Float32,
            )

        # Write data to raster band
        # No data issue: https://gis.stackexchange.com/questions/389587/qgis-set-raster-no-data-value

        try:
            b_count = int(feat.band_count)  # from 2.14
        except:
            b_count = feat["Band count"]

        for i in range(b_count):
            rasterband = np.array(bandValues[i])
            try:
                rasterband = np.reshape(rasterband, (feat.y_size, feat.x_size))
            except:
                rasterband = np.reshape(
                    rasterband, (feat["Y pixels"], feat["X pixels"])
                )

            band = ds.GetRasterBand(
                i + 1
            )  # https://pcjericks.github.io/py-gdalogr-cookbook/raster_layers.html

            # get noDataVal or use default
            try:
                try:
                    noDataVal = float(feat.noDataValue)
                except:
                    noDataVal = float(feat["NoDataVal"][i])  # if value available
                try:
                    band.SetNoDataValue(noDataVal)
                except:
                    band.SetNoDataValue(float(noDataVal))
            except:
                pass

            band.WriteArray(rasterband)  # or "rasterband.T"

        # create GDAL transformation in format [top-left x coord, cell width, 0, top-left y coord, 0, cell height]
        pt = None
        ptSpeckle = None
        try:
            try:
                pt = QgsPoint(feat.x_origin, feat.y_origin, 0)
                ptSpeckle = Point(
                    x=feat.x_origin, y=feat.y_origin, z=0, units=feat.units
                )
            except:
                pt = QgsPoint(feat["X_min"], feat["Y_min"], 0)
                ptSpeckle = Point(
                    x=feat["X_min"], y=feat["Y_min"], z=0, units=feat.units
                )
        except:
            try:
                displayVal = feat.displayValue
            except:
                displayVal = feat["displayValue"]
            if displayVal is not None:
                if isinstance(displayVal[0], Point):
                    pt = pointToNativeWithoutTransforms(
                        displayVal[0], plugin.dataStorage
                    )
                    ptSpeckle = displayVal[0]
                if isinstance(displayVal[0], Mesh):
                    pt = QgsPoint(displayVal[0].vertices[0], displayVal[0].vertices[1])
                    ptSpeckle = Point(
                        x=displayVal[0].vertices[0],
                        y=displayVal[0].vertices[1],
                        z=displayVal[0].vertices[2],
                        units=displayVal[0].units,
                    )
        if pt is None or ptSpeckle is None:
            logToUser(
                "Raster layer doesn't have the origin point",
                level=2,
                plugin=plugin.dockwidget,
            )
            return

        try:  # if the CRS has offset props
            dataStorage.current_layer_crs_offset_x = layer.crs.offset_x
            dataStorage.current_layer_crs_offset_y = layer.crs.offset_y
            dataStorage.current_layer_crs_rotation = layer.crs.rotation

            pt = pointToNative(
                ptSpeckle, sr, plugin.dataStorage
            )  # already transforms the offsets
            dataStorage.current_layer_crs_offset_x = (
                dataStorage.current_layer_crs_offset_y
            ) = dataStorage.current_layer_crs_rotation = None

        except AttributeError as e:
            print(e)
        xform = QgsCoordinateTransform(crs, crsRaster, project)
        pt.transform(xform)
        try:
            ds.SetGeoTransform(
                [pt.x(), feat.x_resolution, 0, pt.y(), 0, feat.y_resolution]
            )
        except:
            ds.SetGeoTransform(
                [pt.x(), feat["X resolution"], 0, pt.y(), 0, feat["Y resolution"]]
            )

        # create a spatial reference object
        ds.SetProjection(crsRasterWkt)
        # close the rater datasource by setting it equal to None
        ds = None

        raster_layer = QgsRasterLayer(fn, finalName, "gdal")
        project.addMapLayer(raster_layer, False)

        # layerGroup = tryCreateGroup(project, streamBranch)
        groupName = streamBranch + SYMBOL + layerName.split(finalName)[0]
        layerGroup = tryCreateGroupTree(project.layerTreeRoot(), groupName, plugin)
        layerGroup.addLayer(raster_layer)

        dataProvider = raster_layer.dataProvider()
        rendererNew = rasterRendererToNative(layer, dataProvider)

        try:
            raster_layer.setRenderer(rendererNew)
        except:
            pass

        try:
            project.removeMapLayer(dummy)
        except:
            pass

        # report on receive:
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{layer.id} {finalName}",
                "obj_type": "Raster Layer",
                "errors": "",
            }
        )
        dataStorage.latestConversionTime = datetime.now()

    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)
        # report on receive:
        dataStorage.latestActionReport.append(
            {
                "speckle_id": f"{layer.id} {finalName}",
                "obj_type": "Raster Layer",
                "errors": f"Receiving layer {layer.name} failed",
            }
        )
        dataStorage.latestConversionTime = datetime.now()
    """

from typing import Any, List, Optional, Tuple, Union
import arcpy
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
from arcpy.management import CreateTable

import os.path

from specklepy.api.credentials import Account, get_local_accounts
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import (
    GraphQLException,
    SpeckleException,
)
from specklepy.api.wrapper import StreamWrapper
from specklepy.api.models import Branch, Stream, Streams
from specklepy.logging import metrics

from osgeo import osr

import inspect

from speckle.speckle.utils.validation import tryGetStream

# from speckle.speckle.speckle_arcgis import SpeckleGIS
from speckle.speckle.converter.layers import getAllProjLayers
from speckle.speckle.utils.panel_logging import logToUser

FIELDS = [
    "project_streams",
    "project_layer_selection",
    "lat_lon",
    "crs_rotation",
    "crs_offsets",
]


def get_project_streams(plugin: "SpeckleGIS", content: str = None):
    try:
        print("GET proj streams")
        project = plugin.project
        table = findOrCreateSpeckleTable(project, plugin)
        logToUser(table, level=0, func=inspect.stack()[0][3])

        rows = arcpy.da.SearchCursor(table, "project_streams")
        saved_streams = []
        for x in rows:
            logToUser(x[0], level=0, func=inspect.stack()[0][3])
            saved_streams.append(x[0])

        temp = []
        ######### need to check whether saved streams are available (account reachable)
        if len(saved_streams) > 0:
            for url in saved_streams:
                if url == "":
                    continue
                try:
                    sw = StreamWrapper(url)
                    try:
                        stream = tryGetStream(sw, plugin.dataStorage)
                    except SpeckleException as e:
                        logToUser(e.message, level=2, func=inspect.stack()[0][3])
                        stream = None
                    # strId = stream.id # will cause exception if invalid
                    temp.append((sw, stream))
                except SpeckleException as e:
                    logToUser(e.message, level=2, func=inspect.stack()[0][3])
                # except GraphQLException as e:
                #    logger.logToUser(e.message, Qgis.Warning)
        plugin.current_streams = temp
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])


def set_project_streams(plugin: "SpeckleGIS"):
    try:
        print("SET proj streams")
        project = plugin.project
        table = findOrCreateSpeckleTable(project, plugin)
        print("SET proj streams 2")

        current_streams = [
            stream[0].stream_url for stream in plugin.current_streams
        ]  # ",".join()
        print(current_streams)
        logToUser(current_streams, level=0, func=inspect.stack()[0][3])

        if table is not None:
            proj_layers = []
            lan_lot = ""
            with arcpy.da.UpdateCursor(table, FIELDS) as cursor:
                for row in cursor:  # just one row
                    if row[1] is not None and row[1] != "":
                        proj_layers.append(row[1])
                    if row[2] is not None and row[2] != "":
                        lan_lot = row[2]
                    cursor.deleteRow()
            del cursor
            if len(proj_layers) == 0:
                proj_layers.append("")
            if len(current_streams) == 0:
                current_streams.append("")

            cursor = arcpy.da.InsertCursor(table, FIELDS[:3])
            length = max(len(proj_layers), len(current_streams))

            for i in range(length):
                if i == 0:
                    cursor.insertRow([current_streams[i], proj_layers[i], lan_lot])
                else:
                    try:
                        cursor.insertRow([current_streams[i], proj_layers[i], ""])
                    except:
                        if len(current_streams) <= i:
                            cursor.insertRow(["", proj_layers[i], ""])
                        if len(proj_layers) <= i:
                            cursor.insertRow([current_streams[i], "", ""])
            del cursor
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])


def get_project_layer_selection(plugin: "SpeckleGIS"):
    try:
        print("GET project layer selection from the table")
        project = plugin.project
        table = findOrCreateSpeckleTable(project, plugin)
        if table is None:
            return

        rows = arcpy.da.SearchCursor(table, "project_layer_selection")
        saved_layers = []
        for x in rows:
            saved_layers.append(x[0])

        temp = []
        proj_layers = getAllProjLayers(plugin)
        if proj_layers is None:
            return
        ######### need to check whether saved streams are available (account reachable)
        if len(saved_layers) > 0:
            for layerPath in saved_layers:
                if layerPath == "":
                    continue
                found = 0
                for layer in proj_layers:
                    print(layer.dataSource)
                    if layer.dataSource == layerPath:
                        temp.append((layer.name, layer))
                        found += 1
                        break
                if found == 0:
                    logToUser(
                        f'Saved layer not found: "{layerPath}"',
                        level=1,
                        func=inspect.stack()[0][3],
                    )
        plugin.dataStorage.current_layers = temp
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])


def set_project_layer_selection(plugin: "SpeckleGIS"):
    try:
        print("SET project layer selection function")
        project = plugin.project
        value: List[str] = [
            layer[1].dataSource for layer in plugin.dataStorage.current_layers
        ]  # ",".join([layer[1].dataSource for layer in plugin.dataStorage.current_layers])
        print(value)

        table = findOrCreateSpeckleTable(project, plugin)
        # print(table)
        if table is not None:
            lan_lot = ""
            proj_streams = []
            with arcpy.da.UpdateCursor(table, FIELDS[:3]) as cursor:
                for row in cursor:  # just one row
                    if row[0] is not None and row[0] != "":
                        proj_streams.append(row[0])
                    if row[2] is not None and row[2] != "":
                        lan_lot = row[2]
                    cursor.deleteRow()
            del cursor
            if len(proj_streams) == 0:
                proj_streams.append("")
            if len(value) == 0:
                value.append("")
            # print(proj_streams)

            cursor = arcpy.da.InsertCursor(table, FIELDS[:3])
            length = max(len(proj_streams), len(value))
            # print(length)
            for i in range(length):
                if i == 0:
                    cursor.insertRow([proj_streams[i], value[i], lan_lot])
                    print(i)
                else:
                    try:
                        cursor.insertRow([proj_streams[i], value[i], ""])
                    except:
                        if len(proj_streams) <= i:
                            cursor.insertRow(["", value[i], ""])
                        if len(value) <= i:
                            cursor.insertRow([proj_streams[i], "", ""])
                # print(i)
            del cursor

            try:
                metrics.track(
                    "Connector Action",
                    plugin.dataStorage.active_account,
                    {
                        "name": "Save Layer Selection",
                        "connector_version": str(plugin.version),
                    },
                )
            except Exception as e:
                logToUser(
                    e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget
                )

            # print(table)
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])

    print("SET project layer selection 2")


def get_rotation(plugin):
    try:
        print("get_rotation")
        dataStorage = plugin.dataStorage
        project = plugin.dataStorage.project
        table = findOrCreateSpeckleTable(project, plugin)
        if table is None:
            return

        rows = arcpy.da.SearchCursor(table, "crs_rotation")
        points = ""
        for x in rows:
            points = x[0]
            break

        if points != "":
            vals: List[str] = points.replace(" ", "").split(";")
            dataStorage.crs_rotation = float(vals)

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)


def set_rotation(plugin):
    try:
        dataStorage = plugin.dataStorage
        project = dataStorage.project
        r = dataStorage.crs_rotation
        if dataStorage.crs_rotation is None:
            r = 0

        table = findOrCreateSpeckleTable(project, plugin)
        if table is not None:
            with arcpy.da.UpdateCursor(table, ["crs_rotation"]) as cursor:
                for row in cursor:  # just one row
                    cursor.updateRow([r])
                    break
            del cursor
        return True

    except Exception as e:
        logToUser("Lat, Lon values invalid: " + str(e), level=2)
        return False


def get_crs_offsets(plugin):
    try:
        print("get_crs_offsets")
        dataStorage = plugin.dataStorage
        project = plugin.dataStorage.project
        table = findOrCreateSpeckleTable(project, plugin)
        if table is None:
            return

        rows = arcpy.da.SearchCursor(table, "crs_offsets")
        points = ""
        for x in rows:
            points = x[0]
            break

        if points != "":
            vals: List[str] = points.replace(" ", "").split(";")[:2]
            dataStorage.crs_offset_x, dataStorage.crs_offset_y = [
                float(i) for i in vals
            ]

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)


def set_crs_offsets(plugin):
    try:

        dataStorage = plugin.dataStorage
        project = dataStorage.project
        x = dataStorage.crs_offset_x
        y = dataStorage.crs_offset_y

        if dataStorage.crs_offset_x is None or dataStorage.crs_offset_y is None:
            x = 0
            y = 0
        pt = str(x) + ";" + str(y)

        table = findOrCreateSpeckleTable(project, plugin)
        if table is not None:
            with arcpy.da.UpdateCursor(table, ["crs_offsets"]) as cursor:
                for row in cursor:  # just one row
                    cursor.updateRow([pt])
                    break
            del cursor

        return True

    except Exception as e:
        logToUser("Lat, Lon values invalid: " + str(e), level=2)
        return False


def get_project_saved_layers(plugin):

    try:
        print("GET project layer selection from the table")
        project = plugin.project
        table = findOrCreateSpeckleTable(project, plugin)
        if table is None:
            return

        rows = arcpy.da.SearchCursor(table, "project_layer_selection")
        saved_layers = []
        for x in rows:
            saved_layers.append(x[0])

        temp = []
        proj_layers = getAllProjLayers(plugin)
        if proj_layers is None:
            return
        ######### need to check whether saved streams are available (account reachable)
        if len(saved_layers) > 0:
            for layerPath in saved_layers:
                if layerPath == "":
                    continue
                found = 0
                for layer in proj_layers:
                    print(layer.dataSource)
                    if layer.dataSource == layerPath:
                        temp.append((layer.name, layer))
                        found += 1
                        break
                if found == 0:
                    logToUser(
                        f'Saved layer not found: "{layerPath}"',
                        level=1,
                        func=inspect.stack()[0][3],
                    )
        # plugin.dataStorage.current_layers = temp
        # plugin.dataStorage.saved_layers = temp
        # plugin.dataStorage.current_layers = temp.copy()
        plugin.dataStorage.saved_layers = temp.copy()
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])


def set_project_saved_layers(plugin):
    return
    try:
        print("SET project layer selection function")
        project = plugin.project
        value: List[str] = [
            layer[1].dataSource for layer in plugin.dataStorage.saved_layers
        ]  # ",".join([layer[1].dataSource for layer in plugin.dataStorage.current_layers])
        if len(value) == 0:
            value.append("")
        print(value)

        table = findOrCreateSpeckleTable(project, plugin)
        # print(table)
        if table is not None:
            cursor = arcpy.da.InsertCursor(table, "project_layer_selection")
            for i in range(len(value)):
                cursor.insertRow([value[i]])
                print(i)
            del cursor

            try:
                metrics.track(
                    "Connector Action",
                    plugin.dataStorage.active_account,
                    {
                        "name": "Save Layer Selection",
                        "connector_version": str(plugin.version),
                    },
                )
            except Exception as e:
                logToUser(
                    e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget
                )
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])


def get_survey_point(plugin: "SpeckleGIS", content=None):
    try:
        print("get survey point")
        project = plugin.dataStorage.project
        table = findOrCreateSpeckleTable(project, plugin)
        if table is None:
            return

        rows = arcpy.da.SearchCursor(table, "lat_lon")
        points = ""
        for x in rows:
            points = x[0]
            break

        if points != "":
            vals: List[str] = points.replace(" ", "").split(";")[:2]
            plugin.lat, plugin.lon = [float(i) for i in vals]

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)


def set_survey_point(plugin: "SpeckleGIS"):

    try:
        # from widget (2 strings) to local vars + update SR of the map
        print("SET survey point")
        dataStorage = plugin.dataStorage
        project = dataStorage.project

        x = dataStorage.custom_lat
        y = dataStorage.custom_lon

        pt = str(x) + ";" + str(y)
        table = findOrCreateSpeckleTable(project, plugin)
        if table is not None:
            with arcpy.da.UpdateCursor(table, ["lat_lon"]) as cursor:
                for row in cursor:  # just one row
                    cursor.updateRow([pt])
                    break
            del cursor
        # setProjectReferenceSystem(plugin)

        try:
            metrics.track(
                "Connector Action",
                plugin.dataStorage.active_account,
                {
                    "name": "Set As Center Point",
                    "connector_version": str(plugin.version),
                },
            )
        except Exception as e:
            logToUser(e, level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)

        return True

    except Exception as e:
        logToUser(
            "Lat, Lon values invalid: " + str(e), level=2, func=inspect.stack()[0][3]
        )
        return False


def setProjectReferenceSystem(plugin: "SpeckleGIS"):
    try:
        # save to project; create SR
        newCrsString = (
            "+proj=tmerc +ellps=WGS84 +datum=WGS84 +units=m +no_defs +lon_0="
            + str(plugin.lon)
            + " lat_0="
            + str(plugin.lat)
            + " +x_0=0 +y_0=0 +k_0=1"
        )
        newCrs = osr.SpatialReference()
        newCrs.ImportFromProj4(newCrsString)
        newCrs.MorphToESRI()  # converts the WKT to an ESRI-compatible format

        validate = True if len(newCrs.ExportToWkt()) > 10 else False

        if validate:
            newProjSR = arcpy.SpatialReference()
            newProjSR.loadFromString(newCrs.ExportToWkt())

            # source = osr.SpatialReference()
            # source.ImportFromWkt(plugin.project.activeMap.spatialReference.exportToString())
            # transform = osr.CoordinateTransformation(source, newCrs)

            plugin.project.activeMap.spatialReference = newProjSR
            logToUser(
                "Custom project Spatial Reference successfully applied",
                level=0,
                func=inspect.stack()[0][3],
                plugin=plugin.dockwidget,
            )
        else:
            logToUser(
                "Custom Spatial Reference could not be created",
                level=1,
                func=inspect.stack()[0][3],
            )

        return True
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return False


def findOrCreateSpeckleTable(project: ArcGISProject, plugin) -> Union[str, None]:
    try:
        path = (
            plugin.workspace
        )  # project.filePath.replace("aprx","gdb") #"\\".join(project.filePath.split("\\")[:-1]) + "\\speckle_layers\\" #arcpy.env.workspace + "\\" #

        if "speckle_gis" not in arcpy.ListTables():
            try:
                table = CreateTable(path, "speckle_gis")
                for f in FIELDS:
                    arcpy.management.AddField(table, f, "TEXT")
                    # arcpy.management.AddField(table, "project_layer_selection", "TEXT")
                    # arcpy.management.AddField(table, "lat_lon", "TEXT")

                cursor = arcpy.da.InsertCursor(table, FIELDS)
                cursor.insertRow(["" for _ in range(len(FIELDS))])
                del cursor

            except Exception as e:
                logToUser(
                    "Error creating a table: " + str(e),
                    level=1,
                    func=inspect.stack()[0][3],
                )
                raise e
        else:
            # print("table already exists")
            # make sure fileds exist
            table = path + "\\speckle_gis"
            for f in FIELDS:
                findOrCreateTableField(table, f)
            # findOrCreateTableField(table, FIELDS[1])
            # findOrCreateTableField(table, FIELDS[2])

            findOrCreateRow(table, FIELDS)

        return table

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None


def findOrCreateTableField(table: str, field: str):
    try:
        with arcpy.da.UpdateCursor(table, [field]) as cursor:
            value = None
            for row in cursor:
                value = row  # tuple(val,)
                if value[0] is None:
                    cursor.updateRow("")
                break  # look at the 1st row only
        del cursor

        # if value is None: # if there are no rows
        #    cursor = arcpy.da.InsertCursor(table, [field])
        #    cursor.insertRow([""])
        #    del cursor

    except Exception as e:  # if field doesn't exist
        arcpy.management.AddField(table, field, "TEXT")
        # cursor = arcpy.da.InsertCursor(table, [field] )
        # cursor.insertRow([""])
        del cursor


def findOrCreateRow(table: str, fields: List[str]):

    # check if the row exists
    cursor = arcpy.da.SearchCursor(table, fields)
    k = -1
    for k, row in enumerate(cursor):
        # print(row)
        break
    del cursor

    # if no rows
    if k == -1:
        cursor = arcpy.da.InsertCursor(table, fields)
        cursor.insertRow(["" for _ in range(len(FIELDS))])
        del cursor
    else:
        with arcpy.da.UpdateCursor(table, fields) as cursor:
            for row in cursor:
                if None in row:
                    cursor.updateRow(["" if r is None else r for r in row])
                break  # look at the 1st row only
        del cursor


def findOrCreateRowInFeatureTable(table: str, fields: List[str], values=None):

    with arcpy.da.UpdateCursor(table, fields) as cursor:
        for row in cursor:
            cursor.deleteRow()
    del cursor

    cursor = arcpy.da.InsertCursor(table, fields)
    cursor.insertRow([str(v) for v in values])
    del cursor

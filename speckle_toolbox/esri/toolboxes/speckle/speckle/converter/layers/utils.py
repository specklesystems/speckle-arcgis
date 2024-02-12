import copy
from datetime import datetime
from typing import Dict, Any, List, Union
import json
import hashlib
from specklepy.objects import Base
from specklepy.objects.geometry import Mesh
from specklepy.objects.other import Collection

import arcpy
from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
import os

import inspect

from PyQt5.QtGui import QColor

from speckle.speckle.converter.layers.emptyLayerTemplates import createGroupLayer
from speckle.speckle.plugin_utils.helpers import findOrCreatePath, SYMBOL
from speckle.speckle.utils.panel_logging import logToUser
from speckle.speckle.plugin_utils.helpers import validateNewFclassName


# ATTRS_REMOVE = ['geometry','applicationId','bbox','displayStyle', 'id', 'renderMaterial', 'displayMesh', 'displayValue']
ATTRS_REMOVE = [
    "speckleTyp",
    "speckle_id",
    "geometry",
    "applicationId",
    "bbox",
    "displayStyle",
    "id",
    "renderMaterial",
    "displayMesh",
    "displayValue",
]


def generate_qgis_app_id(
    base: Base,
    layer,
    f,
):
    """Generate unique ID for Vector feature."""
    return ""
    try:
        fieldnames = [str(field.name()) for field in layer.fields()]
        props = [str(f[prop]) for prop in fieldnames]
        try:
            geoms = f.geometry()
        except Exception as e:
            geoms = ""

        id_data: str = (
            layer.id()
            + str(layer.wkbType())
            + str(fieldnames)
            + str(props)
            + str(geoms)
        )
        return hashlib.md5(id_data.encode("utf-8")).hexdigest()

    except Exception as e:
        logToUser(
            f"Application ID not generated for feature in layer {layer.name()}: {e}",
            level=1,
        )
        return ""


def generate_qgis_raster_app_id(rasterLayer):
    """Generate unique ID for Raster layer."""
    return ""
    try:
        id_data = str(get_raster_stats(rasterLayer))
        file_ds = gdal.Open(rasterLayer.source(), gdal.GA_ReadOnly)
        for i in range(rasterLayer.bandCount()):
            band = file_ds.GetRasterBand(i + 1)
            id_data += str(band.ReadAsArray())
        return hashlib.md5(id_data.encode("utf-8")).hexdigest()

    except Exception as e:
        logToUser(
            f"Application ID not generated for layer {rasterLayer.name()}: {e}",
            level=1,
        )
        return ""


def findUpdateJsonItemPath(tree: Dict, full_path_str: str):
    try:
        new_tree = copy.deepcopy(tree)

        path_list_original = full_path_str.split(SYMBOL)
        path_list = []
        for x in path_list_original:
            if len(x) > 0:
                path_list.append(x)
        attr_found = False

        for i, item in enumerate(new_tree.items()):
            attr, val_dict = item

            if attr == path_list[0]:
                attr_found = True
                path_list.pop(0)
                if len(path_list) > 0:  # if the path is not finished:
                    all_names = val_dict.keys()
                    if (
                        len(path_list) == 1 and path_list[0] in all_names
                    ):  # already in a tree
                        return new_tree
                    else:
                        branch = findUpdateJsonItemPath(
                            val_dict, SYMBOL.join(path_list)
                        )
                        new_tree.update({attr: branch})

        if (
            attr_found is False and len(path_list) > 0
        ):  # create a new branch at the top level
            if len(path_list) == 1:
                new_tree.update({path_list[0]: {}})
                return new_tree
            else:
                branch = findUpdateJsonItemPath(
                    {path_list[0]: {}}, SYMBOL.join(path_list)
                )
                new_tree.update(branch)
        return new_tree
    except Exception as e:
        # logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return tree


def collectionsFromJson(
    jsonObj: dict, levels: list, layerConverted, baseCollection: Collection
):
    if jsonObj == {} or len(levels) == 0:
        # print("RETURN")
        baseCollection.elements.append(layerConverted)
        return baseCollection

    lastLevel = baseCollection
    for i, l in enumerate(levels):
        sub_collection_found = 0
        for item in lastLevel.elements:
            # print("___ITEM")
            # print(l)
            if item.name == l:
                # print("___ITEM FOUND")
                # print(l)
                lastLevel = item
                sub_collection_found = 1
                break
        if sub_collection_found == 0:
            # print("___ SUB COLLECTION NOT FOUND")
            subCollection = Collection(
                units="m", collectionType="ArcGIS Layer Group", name=l, elements=[]
            )
            lastLevel.elements.append(subCollection)
            lastLevel = lastLevel.elements[
                len(lastLevel.elements) - 1
            ]  # reassign last element

        if i == len(levels) - 1:  # if last level
            lastLevel.elements.append(layerConverted)

    return baseCollection


def findAndClearLayerGroup(project: ArcGISProject, newGroupName: str = "", plugin=None):
    print("find And Clear LayerGroup")
    try:
        groupExists = 0
        # print(newGroupName)
        for l in project.activeMap.listLayers():
            # print(l.longName)
            if l.longName.startswith(newGroupName + "\\"):
                # print(l.longName)
                if l.isFeatureLayer:
                    # condition for feature layers:
                    fields = [f.name for f in arcpy.ListFields(l.dataSource)]
                    # print(fields)
                    if "Speckle_ID" in fields or "speckle_id" in fields:
                        project.activeMap.removeLayer(l)
                        groupExists += 1
                elif l.isRasterLayer:
                    # condition for raster layers:
                    if "_Speckle" in l.name:
                        project.activeMap.removeLayer(l)
                        groupExists += 1

            elif l.longName == newGroupName:
                groupExists += 1
        # print(newGroupName)
        if groupExists == 0:
            layerGroup = create_layer_group(project, newGroupName, plugin)

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3], plugin=plugin.dockwidget)


def create_layer_group(project: ArcGISProject, newGroupName: str, plugin):
    try:
        path: str = (
            os.path.expandvars(r"%LOCALAPPDATA%")
            + "\\Temp\\Speckle_ArcGIS_temp\\"
            + datetime.now().strftime("%Y-%m-%d_%H-%M")
        )
        path += "\\Layers_Speckle\\"
        findOrCreatePath(path)
        lyr_path = path + newGroupName + ".lyrx"
        # print(lyr_path)
        r"""
        try:
            f = open(lyr_path, "w")
            content = createGroupLayer().replace("TestGroupLayer", newGroupName)
            f.write(content)
            f.close()
            newGroupLayer = arcpy.mp.LayerFile(lyr_path)
            layerGroup = project.activeMap.addLayer(newGroupLayer)[0]
            print(layerGroup)
            return layerGroup
        except:  # for 3.0.0
        """
        if project.activeMap is not None:
            # print("try creating the group")
            # check for full match
            for l in project.activeMap.listLayers():
                # print(newGroupName + "  __  " + l.longName)
                if l.longName == newGroupName and l.isGroupLayer:
                    layerGroup = l
                    return layerGroup
            # check for parent layer
            for l in project.activeMap.listLayers():
                # print(newGroupName + "  __  " + l.longName)
                if (
                    l.longName == "\\".join(newGroupName.split("\\")[:-1])
                    and l.isGroupLayer
                ):
                    short_name = newGroupName.split("\\")[-1]
                    new_group = project.activeMap.createGroupLayer(short_name, l)
                    return new_group

            layerGroup = project.activeMap.createGroupLayer(newGroupName)
            # print(layerGroup)
            return layerGroup
        else:
            logToUser(
                "The map didn't fully load, try selecting the project Map or/and refreshing the plugin.",
                level=1,
                func=inspect.stack()[0][3],
            )
            return
    except Exception as e:
        print(e)


def getVariantFromValue(value: Any) -> Union[str, None]:
    # print("_________get variant from value_______")
    # TODO add Base object
    res = None
    try:
        pairs = [(str, "TEXT"), (float, "FLOAT"), (int, "LONG"), (bool, "SHORT")]  # 10
        for p in pairs:
            if isinstance(value, p[0]):
                res = p[1]
                try:
                    if res == "LONG" and (value >= 2147483647 or value <= -2147483647):
                        # https://pro.arcgis.com/en/pro-app/latest/help/data/geodatabases/overview/arcgis-field-data-types.htm
                        res = "FLOAT"
                except Exception as e:
                    print(e)
                break

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])

    return res


def colorFromSpeckle(rgb):
    try:
        color = QColor.fromRgb(245, 245, 245)
        if isinstance(rgb, int):
            r = (rgb & 0xFF0000) >> 16
            g = (rgb & 0xFF00) >> 8
            b = rgb & 0xFF
            color = QColor.fromRgb(r, g, b)
        return color
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return QColor.fromRgb(245, 245, 245)


def getDisplayValueList(geom: Any) -> List:
    try:
        # print("___getDisplayValueList")
        val = []
        # get list of display values for Meshes
        if isinstance(geom, Mesh):
            val = [geom]
        elif isinstance(geom, List) and len(geom) > 0:
            if isinstance(geom[0], Mesh):
                val = geom
            else:
                print("not an individual geometry")
        else:
            try:
                val = geom.displayValue  # list
            except Exception as e:
                # print(e)
                try:
                    val = geom["@displayValue"]  # list
                except Exception as e:
                    # print(e)
                    try:
                        val = geom.displayMesh
                    except:
                        pass
        return val
    except Exception as e:
        # print(e)
        return []


def getLayerGeomType(layer) -> str:
    return


def tryCreateGroupTree(project: ArcGISProject, fullGroupName, plugin=None):

    # CREATE A GROUP "received blabla" with sublayers
    # print("_________CREATE GROUP TREE: " + fullGroupName)

    # receive_layer_tree: dict = plugin.receive_layer_tree
    receive_layer_list = fullGroupName.split(SYMBOL)
    path_list = []
    for x in receive_layer_list:
        if len(x) > 0:
            path_list.append(x)
    group_to_create_name = path_list[0]
    layerGroup = create_layer_group(project, group_to_create_name, plugin)
    path_list.pop(0)

    if len(path_list) > 0:
        path_list[0] = f"{group_to_create_name}\\{path_list[0]}"
        layerGroup = tryCreateGroupTree(project, SYMBOL.join(path_list), plugin)

    return layerGroup


def validateAttributeName(name: str, fieldnames: List[str]) -> str:
    try:
        new_list = [x for x in fieldnames if x != name]

        corrected = name.replace("/", "_").replace(".", "_")
        if corrected == "id":
            corrected = "applicationId"

        for i, x in enumerate(corrected):
            if corrected[0] != "_" and corrected not in new_list:
                break
            else:
                corrected = corrected[1:]

        if len(corrected) <= 1 and len(name) > 1:
            corrected = "0" + name  # if the loop removed the property name completely

        return corrected
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def trySaveCRS(crs, streamBranch: str = ""):
    return
    try:
        authid = crs.authid()
        wkt = crs.toWkt()
        if authid == "":
            crs_id = crs.saveAsUserCrs("SpeckleCRS_" + streamBranch)
            return crs_id
        else:
            return crs.srsid()
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3])
        return


def getLayerAttributes(
    featuresList: List[Base], attrsToRemove: List[str] = ATTRS_REMOVE
) -> Dict[str, str]:
    print("03________ get layer attributes")
    fields = {}
    try:
        if not isinstance(featuresList, list):
            features = [featuresList]
        else:
            features = featuresList[:]
        # print(features)
        all_props = []
        for feature in features:
            # get object properties to add as attributes
            try:
                dynamicProps = (
                    feature.attributes.get_dynamic_member_names()
                )  # for 2.14 onwards
            except:
                dynamicProps = feature.get_dynamic_member_names()

            for att in ATTRS_REMOVE:
                try:
                    dynamicProps.remove(att)
                except ValueError:
                    pass

            dynamicProps.sort()

            # add field names and variands
            for name in dynamicProps:
                # if name not in all_props: all_props.append(name)

                try:
                    value = feature.attributes[name]
                except:
                    value = feature[name]
                variant = getVariantFromValue(value)
                # if name == 'area': print(value); print(variant)
                if not variant:
                    variant = None  # LongLong #4

                # go thought the dictionary object
                if value and isinstance(value, list):
                    # all_props.remove(name) # remove generic dict name
                    for i, val_item in enumerate(value):
                        newF, newVals = traverseDict(
                            {}, {}, name + "_" + str(i), val_item
                        )

                        for i, (k, v) in enumerate(newF.items()):
                            if k not in all_props:
                                all_props.append(k)
                            if k not in fields.keys():
                                fields.update({k: v})
                            else:  # check if the field was empty previously:
                                oldVariant = fields[k]
                                # replace if new one is NOT Float (too large integers)
                                # if oldVariant != "FLOAT" and v == "FLOAT":
                                #    fields.update({k: v})
                                # replace if new one is NOT LongLong or IS String
                                if oldVariant != "TEXT" and v == "TEXT":
                                    fields.update({k: v})

                # add a field if not existing yet
                else:  # if str, Base, etc
                    newF, newVals = traverseDict({}, {}, name, value)

                    for i, (k, v) in enumerate(newF.items()):
                        if k not in all_props:
                            all_props.append(k)
                        if k not in fields.keys():
                            fields.update({k: v})  # if variant is known
                        else:  # check if the field was empty previously:
                            oldVariant = fields[k]
                            # replace if new one is NOT Float (too large integers)
                            # print(oldVariant, v)
                            # if oldVariant == "LONG" and v == "FLOAT":
                            #    fields.update({k: v})
                            # replace if new one is NOT LongLong or IS String
                            if oldVariant != "TEXT" and v == "TEXT":
                                fields.update({k: v})
                            # print(fields)
        # replace all empty ones wit String
        all_props.append("Speckle_ID")
        for name in all_props:
            if name not in fields.keys():
                fields.update({name: "TEXT"})
        # print(fields)
        # fields_sorted = {k: v for k, v in sorted(fields.items(), key=lambda item: item[0])}
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return fields


def traverseDict(newF: dict, newVals: dict, nam: str, val: Any):
    try:
        if isinstance(val, dict):
            for i, (k, v) in enumerate(val.items()):
                newF, newVals = traverseDict(newF, newVals, nam + "_" + k, v)
        elif isinstance(val, Base):
            dynamicProps = val.get_dynamic_member_names()
            for att in ATTRS_REMOVE:
                try:
                    dynamicProps.remove(att)
                except:
                    pass
            dynamicProps.sort()

            item_dict = {}
            for prop in dynamicProps:
                item_dict.update({prop: val[prop]})

            for i, (k, v) in enumerate(item_dict.items()):
                newF, newVals = traverseDict(newF, newVals, nam + "_" + k, v)
        else:
            var = getVariantFromValue(val)
            if var is None:
                var = "TEXT"
                val = str(val)
            # print(var)
            newF.update({nam: var})
            newVals.update({nam: val})

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return newF, newVals


def get_scale_factor(units: str) -> float:
    unit_scale = {
        "meters": 1.0,
        "centimeters": 0.01,
        "millimeters": 0.001,
        "inches": 0.0254,
        "feet": 0.3048,
        "kilometers": 1000.0,
        "mm": 0.001,
        "cm": 0.01,
        "m": 1.0,
        "km": 1000.0,
        "in": 0.0254,
        "ft": 0.3048,
        "yd": 0.9144,
        "mi": 1609.340,
    }
    if units is not None and units.lower() in unit_scale.keys():
        return unit_scale[units]
    logToUser(
        f"Units {units} are not supported. Meters will be applied by default.",
        level=0,
        func=inspect.stack()[0][3],
    )
    return 1.0


def findTransformation(
    f_shape,
    geomType,
    layer_sr: arcpy.SpatialReference,
    projectCRS: arcpy.SpatialReference,
    selectedLayer: arcLayer,
):
    # apply transformation if needed
    try:
        if layer_sr.name != projectCRS.name:
            tr0 = tr1 = tr2 = tr_custom = None
            midSr = arcpy.SpatialReference("WGS 1984")  # GCS_WGS_1984
            # print(layer_sr)
            try:
                transformations = arcpy.ListTransformations(layer_sr, projectCRS)
                # print(transformations)
                customTransformName = "layer_sr.name" + "_To_" + projectCRS.name
                if len(transformations) == 0:
                    try:
                        tr1 = arcpy.ListTransformations(layer_sr, midSr)[0]
                        tr2 = arcpy.ListTransformations(midSr, projectCRS)[0]
                    except:
                        # customGeoTransfm = "GEOGTRAN[METHOD['Geocentric_Translation'],PARAMETER['X_Axis_Translation',''],PARAMETER['Y_Axis_Translation',''],PARAMETER['Z_Axis_Translation','']]"
                        # CreateCustomGeoTransformation(customTransformName, layer_sr, projectCRS)
                        tr_custom = customTransformName
                else:
                    # print("else")
                    # choose equation based instead of file-based/grid-based method,
                    # to be consistent with QGIS: https://desktop.arcgis.com/en/arcmap/latest/map/projections/choosing-an-appropriate-transformation.htm
                    selecterTr = {}
                    for tr in transformations:
                        if "NTv2" not in tr and "NADCON" not in tr:
                            set1 = set(
                                layer_sr.name.split("_") + projectCRS.name.split("_")
                            )
                            set2 = set(tr.split("_"))
                            diff = len(set(set1).symmetric_difference(set2))
                            selecterTr.update({tr: diff})
                    selecterTr = dict(
                        sorted(selecterTr.items(), key=lambda item: item[1])
                    )
                    tr0 = list(selecterTr.keys())[0]

                if (
                    geomType != "Point"
                    and geomType != "Polyline"
                    and geomType != "Polygon"
                    and geomType != "Multipoint"
                    and geomType != "MultiPatch"
                ):
                    try:
                        logToUser(
                            "Unsupported or invalid geometry in layer "
                            + selectedLayer.name,
                            level=2,
                            func=inspect.stack()[0][3],
                        )
                    except:
                        logToUser(
                            "Unsupported or invalid geometry",
                            level=2,
                            func=inspect.stack()[0][3],
                        )

                # reproject geometry using chosen transformstion(s)
                if tr0 is not None:
                    ptgeo1 = f_shape.projectAs(projectCRS, tr0)
                    f_shape = ptgeo1
                elif tr1 is not None and tr2 is not None:
                    ptgeo1 = f_shape.projectAs(midSr, tr1)
                    ptgeo2 = ptgeo1.projectAs(projectCRS, tr2)
                    f_shape = ptgeo2
                else:
                    ptgeo1 = f_shape.projectAs(projectCRS)
                    f_shape = ptgeo1

            except:
                logToUser(
                    f"Spatial Transformation not found for layer {selectedLayer.name}",
                    level=2,
                    func=inspect.stack()[0][3],
                )
                return None

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return f_shape


def traverseDictByKey(d: Dict, key: str = "", result=None) -> Dict:
    print("__traverse")
    try:
        result = None
        # print(d)
        for k, v in d.items():

            try:
                v = json.loads(v)
            except:
                pass
            if isinstance(v, dict):
                # print("__dict__")
                if k == key:
                    print("__break loop")
                    result = v
                    return result
                else:
                    result = traverseDictByKey(v, key, result)
                    if result is not None:
                        return result
            if isinstance(v, list):
                for item in v:
                    # print(item)
                    if isinstance(item, dict):
                        result = traverseDictByKey(item, key, result)
                        if result is not None:
                            return result
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None
    # print("__result is: ____________")
    # return result


def hsv_to_rgb(listHSV):
    try:
        h, s, v = listHSV[0], listHSV[1], listHSV[2]
        if s == 0.0:
            v *= 255
            return (v, v, v)
        i = int(h * 6.0)  # XXX assume int() truncates!
        f = (h * 6.0) - i
        p, q, t = (
            int(255 * (v * (1.0 - s))),
            int(255 * (v * (1.0 - s * f))),
            int(255 * (v * (1.0 - s * (1.0 - f)))),
        )
        v *= 255
        i %= 6
        if i == 0:
            return (v, t, p)
        if i == 1:
            return (q, v, p)
        if i == 2:
            return (p, v, t)
        if i == 3:
            return (p, q, v)
        if i == 4:
            return (t, p, v)
        if i == 5:
            return (v, p, q)

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return (0, 0, 0)


def cmyk_to_rgb(c, m, y, k, cmyk_scale, rgb_scale=255):
    try:
        r = rgb_scale * (1.0 - c / float(cmyk_scale)) * (1.0 - k / float(cmyk_scale))
        g = rgb_scale * (1.0 - m / float(cmyk_scale)) * (1.0 - k / float(cmyk_scale))
        b = rgb_scale * (1.0 - y / float(cmyk_scale)) * (1.0 - k / float(cmyk_scale))
        return r, g, b
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return 0, 0, 0


def newLayerGroupAndName(
    layerName: str, streamBranch: str, project: ArcGISProject
) -> str:
    print("___new Layer Group and Name")
    layerGroup = None
    newGroupName = f"{streamBranch}"
    try:
        # CREATE A GROUP "received blabla" with sublayers
        print(newGroupName)
        for l in project.activeMap.listLayers():
            if l.longName == newGroupName:
                layerGroup = l
                break

        # find a layer with a matching name in the "latest" group
        newName = (
            f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'
        )

        all_layer_names = []
        layerExists = 0
        for l in project.activeMap.listLayers():
            if l.longName.startswith(newGroupName + "\\"):
                all_layer_names.append(l.longName)
        # print(all_layer_names)
        print(newName)

        newName = validateNewFclassName(newName, all_layer_names, streamBranch + "\\")

        print(newName)
        return newName, layerGroup
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None, None


def curvedFeatureClassToSegments(layer) -> str:
    print("___densify___")
    try:
        data = arcpy.Describe(layer.dataSource)
        dataPath = data.catalogPath
        print(dataPath)
        newPath = dataPath + "_backup"

        arcpy.management.CopyFeatures(
            dataPath, newPath
        )  # features copied like this do not preserve curved segments

        arcpy.edit.Densify(
            in_features=newPath,
            densification_method="ANGLE",
            max_angle=0.01,
            max_vertex_per_segment=100,
        )  # https://pro.arcgis.com/en/pro-app/latest/tool-reference/editing/densify.htm
        print(newPath)
        return newPath

    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None


def validate_path(path: str, plugin):
    """If our path contains a DB name, make sure we have a valid DB name and not a standard file name."""
    try:
        # https://github.com/EsriOceans/btm/commit/a9c0529485c9b0baa78c1f094372c0f9d83c0aaf
        dirname, file_name = os.path.split(path)
        # print(dirname)
        # print(file_name)
        file_base = os.path.splitext(file_name)[0]
        if dirname == "":
            # a relative path only, relying on the workspace
            dirname = plugin.workspace
        path_ext = os.path.splitext(dirname)[1].lower()
        if path_ext in [".mdb", ".gdb", ".sde"]:
            # we're working in a database
            file_name = arcpy.ValidateTableName(
                file_base
            )  # e.g. add a letter in front of the name
        validated_path = os.path.join(dirname, file_name)
        # msg("validated path: %s; (from %s)" % (validated_path, path))
        return validated_path
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
        return None

"""
Contains all Layer related classes and methods.
"""

from typing import Any, List, Tuple, Union

import inspect

from speckle.speckle.plugin_utils.helpers import (
    SYMBOL,
)
from speckle.speckle.utils.panel_logging import logToUser

from arcpy._mp import ArcGISProject, Map, Layer as arcLayer


def getAllProjLayers(plugin) -> List[arcLayer]:
    # print("get all project layers")
    layers = []
    try:
        project: ArcGISProject = plugin.project
        if project.activeMap is not None and isinstance(
            project.activeMap, Map
        ):  # if project loaded
            # print(type(project.activeMap))
            for layer in project.activeMap.listLayers():
                if (layer.isFeatureLayer) or layer.isRasterLayer:
                    layers.append(layer)  # type: 'arcpy._mp.Layer'
        else:
            # print(type(project.activeMap))
            logToUser(
                "Cannot get Project layers, Project Active Map not loaded or not selected",
                level=1,
                func=inspect.stack()[0][3],
                plugin=plugin.dockwidget,
            )
            return None
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return layers


def getLayersWithStructure(
    plugin, bySelection=False
) -> Tuple[List[arcLayer], List[str]]:
    """Gets a list of all layers in the map"""
    layers = []
    structure = []
    try:
        print("___ get layers list ___")

        # issue with getting selected layers: https://community.esri.com/t5/python-questions/determining-selected-layers-in-the-table-of/td-p/252098

        self = plugin.dockwidget
        project = plugin.project
        map = project.activeMap
        if map is None:
            logToUser(
                "Project Active Map not loaded or not selected",
                level=2,
                func=inspect.stack()[0][3],
            )
            return None, None

        if bySelection is True:  # by selection
            # print("get selected layers")
            for layer in project.activeMap.listLayers():
                if layer.visible and (layer.isFeatureLayer or layer.isRasterLayer):

                    # find possibly hidden parent groups
                    layerGroupsHidden = 0
                    for group in project.activeMap.listLayers():
                        if (
                            layer.longName.startswith(group.longName + "\\")
                            and group.visible is False
                        ):
                            for sub_layer in group.listLayers():
                                if sub_layer.longName == layer.longName:
                                    layerGroupsHidden += 1
                                    break
                            # .isGroupLayer method is broken: https://community.esri.com/t5/python-questions/arcpy-property-layer-isgrouplayer-not-working-as/td-p/709250
                            r""" 
                            if group.isGroupLayer:
                                print("__groups")
                                print(group.longName + "_" + str(group.visible))
                                if layer.longName.startswith(group.longName + "\\"):
                                    print(group.visible)
                                    if group.visible is False:
                                        layerGroupsHidden += 1
                                        break
                            """
                    if layerGroupsHidden == 0:
                        layers.append(layer)
                        structure.append(
                            ("\\".join(layer.longName.split("\\")[:-1]) + "\\").replace(
                                "\\", SYMBOL
                            )
                        )
            # print("layers selected and saved")
        else:  # from project data
            # all_layers_ids = [l.id() for l in project.mapLayers().values()]
            for item in plugin.dataStorage.current_layers:
                try:
                    layerPath = item[1].dataSource

                    found = 0

                    all_layers = getAllProjLayers(plugin)
                    if all_layers is None:
                        return None
                    for l in all_layers:
                        if l.dataSource == layerPath:
                            layers.append(l)
                            structure.append(
                                "\\".join(l.longName.split("\\")[:-1] + "\\").replace(
                                    "\\", SYMBOL
                                )
                            )
                            found += 1
                            break
                    if found == 0:
                        logToUser(
                            f'Saved layer not found: "{item[0]}"',
                            level=1,
                            func=inspect.stack()[0][3],
                        )

                except:
                    logToUser(
                        f'Saved layer not found: "{item[0]}"',
                        level=1,
                        func=inspect.stack()[0][3],
                    )
                    continue
    except Exception as e:
        logToUser(str(e), level=2, func=inspect.stack()[0][3])
    return layers, structure

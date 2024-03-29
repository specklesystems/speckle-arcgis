import os
from typing import List
import inspect

SYMBOL = "_x_x_"
UNSUPPORTED_PROVIDERS = ["WFS", "wms", "wcs", "vectortile"]


def get_scale_factor(units: str, dataStorage) -> float:
    scale_to_meter = get_scale_factor_to_meter(units)
    if dataStorage is not None:
        scale_back = scale_to_meter / get_scale_factor_to_meter(
            dataStorage.currentUnits
        )
        return scale_back
    else:
        return scale_to_meter


def get_scale_factor_to_meter(units: str) -> float:
    try:
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
        if (
            units is not None
            and isinstance(units, str)
            and units.lower() in unit_scale.keys()
        ):
            return unit_scale[units]
        try:
            from speckle.speckle.utils.panel_logging import logToUser

            logToUser(
                f"Units {units} are not supported. Meters will be applied by default.",
                level=1,
                func=inspect.stack()[0][3],
            )
            return 1.0
        except:
            print(
                f"Units {units} are not supported. Meters will be applied by default."
            )
            return 1.0
    except Exception as e:
        try:
            from speckle.speckle.utils.panel_logging import logToUser

            logToUser(
                f"{e}. Meters will be applied by default.",
                level=2,
                func=inspect.stack()[0][3],
            )
            return 1.0
        except:
            print(f"{e}. Meters will be applied by default.")
            return 1.0


def getAppName(name: str) -> str:
    new_name = ""
    for i, x in enumerate(str(name)):
        if x.lower() in [a for k, a in enumerate("abcdefghijklmnopqrstuvwxyz")]:
            new_name += x
        else:
            break
    return new_name


def findOrCreatePath(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def removeSpecialCharacters(text: str) -> str:
    new_text = (
        text.replace("[", "_")
        .replace("]", "_")
        .replace(".", "_")
        .replace(" ", "_")
        .replace("-", "_")
        .replace("—", "_")
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
    # new_text = text.encode('iso-8859-1', errors='ignore').decode('utf-8')
    return new_text


def splitTextIntoLines(text: str = "", number: int = 40) -> str:
    print("__splitTextIntoLines")
    print(text)
    msg = ""
    try:
        if len(text) > number:
            try:
                for i, x in enumerate(text):
                    msg += x
                    if i != 0 and i % number == 0:
                        msg += "\n"
            except Exception as e:
                print(e)
        else:
            msg = text
    except Exception as e:
        print(e)
        print(text)

    return msg


def jsonFromList(jsonObj: dict, levels: list):
    # print("jsonFromList")
    if len(levels) == 0:
        return jsonObj
    lastLevel = jsonObj
    for l in levels:
        # print(lastLevel)
        try:
            lastLevel = lastLevel[l]
        except:
            lastLevel.update({l: {}})
    # print(jsonObj)
    return jsonObj


def validateNewFclassName(
    newName: str, all_layer_names: List[str], prefix: str = ""
) -> str:

    fixed_name = newName

    if (prefix + fixed_name) in all_layer_names:

        layerNameCreated = 0
        for index, letter in enumerate("234567890abcdefghijklmnopqrstuvwxyz"):
            if ((prefix + fixed_name) + "_" + letter) not in all_layer_names:
                fixed_name += "_" + letter
                layerNameCreated += 1
                break
        if layerNameCreated == 0:
            for index, letter in enumerate("234567890abcdefghijklmnopqrstuvwxyz"):
                test_fixed_name = validateNewFclassName(
                    (fixed_name + "_" + letter), all_layer_names, prefix
                )
                if (prefix + test_fixed_name) not in all_layer_names:
                    fixed_name = test_fixed_name
                    layerNameCreated += 1
                    break
                # else: layerNameCreated +=1

        if layerNameCreated == 0:
            pass  # logToUser('Feature class name already exists', level=2, func = inspect.stack()[0][3])
            # return fixed_name

    return fixed_name


def findFeatColors(fetColors, f):

    colorFound = 0
    try:  # get render material from any part of the mesh (list of items in displayValue)
        for k, item in enumerate(f.displayValue):
            try:
                fetColors.append(item.renderMaterial.diffuse)
                colorFound += 1
                break
            except:
                pass
        if colorFound == 0:
            fetColors.append(f.renderMaterial.diffuse)
    except:
        try:
            for k, item in enumerate(f["@displayValue"]):
                try:
                    fetColors.append(item.renderMaterial.diffuse)
                    colorFound += 1
                    break
                except:
                    pass
            if colorFound == 0:
                fetColors.append(f.renderMaterial.diffuse)
        except:
            # the Mesh itself has a renderer
            try:  # get render material from any part of the mesh (list of items in displayValue)
                fetColors.append(f.renderMaterial.diffuse)
                colorFound += 1
            except:
                try:
                    fetColors.append(f.displayStyle.color)
                    colorFound += 1
                except:
                    pass
    if colorFound == 0:
        fetColors.append(None)
    return fetColors

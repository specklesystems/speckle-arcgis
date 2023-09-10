
from typing import Any, Callable, List, Optional 

import inspect 

from specklepy.objects import Base

try:
    from speckle.ui.logger import logToUser
    from speckle.converter.layers.Layer import VectorLayer, RasterLayer, Layer
    from speckle.converter.layers import bimLayerToNative, cadLayerToNative, layerToNative
except:
    from speckle_toolbox.esri.toolboxes.speckle.ui.logger import logToUser
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.Layer import VectorLayer, RasterLayer, Layer
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers import bimLayerToNative, cadLayerToNative, layerToNative

import arcpy

SPECKLE_TYPES_TO_READ = ["Objects.Geometry.", "Objects.BuiltElements.", "IFC"] # will properly traverse and check for displayValue

def traverseObject(
    base: Base,
    callback: Optional[Callable[[Base, str, Any], bool]],
    check: Optional[Callable[[Base], bool]],
    streamBranch: str,
    plugin=None,
):
    try:
        #print("traverse Object")
        #print(base)
        if check and check(base):
            res = callback(base, streamBranch, plugin) if callback else False
            #print(res)
            if res:
                return
        memberNames = base.get_member_names()
        #print(base)
        #print(memberNames)
        for name in memberNames:
            try:
                if ["id", "applicationId", "units", "speckle_type"].index(name):
                    continue
            except:
                pass
            #print(name)
            traverseValue(base[name], callback, check, streamBranch, plugin)
        logToUser("Data received", level=0)
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])

def traverseValue(
    value: Any,
    callback: Optional[Callable[[Base, str, Any], bool]],
    check: Optional[Callable[[Base], bool]],
    streamBranch: str,
    plugin = None,
):
    try:
        #print("traverse Value")
        #print(value)
        if isinstance(value, Base):
            traverseObject(value, callback, check, streamBranch, plugin)
        if isinstance(value, List):
            for item in value:
                traverseValue(item, callback, check, streamBranch, plugin)
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])

def callback(base: Base, streamBranch: str, plugin=None) -> bool:
    try:
        #print("callback")
        if base.speckle_type.endswith("VectorLayer") or base.speckle_type.endswith("RasterLayer"):
            if isinstance(base, Layer):
                logToUser(f"Speckle class \"Layer\" will be deprecated in future updates in favour of \"VectorLayer\" or \"RasterLayer\"", level=0, func = inspect.stack()[0][3]) 
            layerToNative(base, streamBranch, plugin)
            #print(layer)
            #if layer is not None:
            #    logToUser("Layer created: " + layer.name(), level=0)
        else:
            loopObj(base, "", streamBranch, plugin)
        return True
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
        return False

def loopObj(base: Base, baseName: str, streamBranch: str, plugin=None):
    try:
        memberNames = base.get_member_names()
        for name in memberNames:
            if name in ["id", "applicationId", "units", "speckle_type"]: continue
            # skip if traversal goes to displayValue of an object, that will be readable anyway:
            if not isinstance(base, Base): logToUser("NOT BASE: "+type(base), level=1, func = inspect.stack()[0][3]); continue
            if (name == "displayValue" or name == "@displayValue") and base.speckle_type.startswith(tuple(SPECKLE_TYPES_TO_READ)): continue 

            try: loopVal(base[name], baseName + "/" + name, streamBranch, plugin)
            except: pass
    
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])

def loopVal(value: Any, name: str, streamBranch: str, plugin=None): # "name" is the parent object/property/layer name
    try:
        if isinstance(value, Base): 
            try: # loop through objects with Speckletype prop, but don't go through parts of Speckle Geometry object
                if not value.speckle_type.startswith("Objects.Geometry."): 
                    loopObj(value, name, streamBranch, plugin)
            except: 
                loopObj(value, name, streamBranch, plugin)

        elif isinstance(value, List):
            streamBranch = streamBranch.replace("[","_").replace("]","_").replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_")

            objectListConverted = 0
            #print("loop val - List")
            for i, item in enumerate(value):
                loopVal(item, name, streamBranch, plugin)
                if not isinstance(item, Base): continue
                if item.speckle_type and item.speckle_type.startswith("IFC"): 
                    # keep traversing infinitely, just don't run repeated conversion for the same list of objects
                    try: 
                        if item["displayValue"] is not None and objectListConverted == 0: 
                            bimLayerToNative(value, name, streamBranch, None, plugin)
                            objectListConverted += 1
                    except: 
                        try: 
                            if item["@displayValue"] is not None and objectListConverted == 0: 
                                bimLayerToNative(value, name, streamBranch, None, plugin)
                                objectListConverted += 1
                        except: pass 
                elif item.speckle_type and item.speckle_type.endswith(".ModelCurve"): 
                    if item["baseCurve"] is not None: 
                        cadLayerToNative(value, name, streamBranch, plugin)
                        break
                elif item.speckle_type and (item.speckle_type == "Objects.Geometry.Mesh" or item.speckle_type == "Objects.Geometry.Brep" or item.speckle_type.startswith("Objects.BuiltElements.")):
                    bimLayerToNative(value, name, streamBranch, None, plugin)
                    break
                elif item.speckle_type and item.speckle_type != "Objects.Geometry.Mesh" and item.speckle_type != "Objects.Geometry.Brep" and item.speckle_type.startswith("Objects.Geometry."): # or item.speckle_type == 'Objects.BuiltElements.Alignment'): 
                    cadLayerToNative(value, name, streamBranch, plugin)
                    #if pt is not None: arcpy.AddMessage("Layer group created: " + str(pt.name))
                    #if pl is not None: arcpy.AddMessage("Layer group created: " + str(pl.name))
                    break
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])


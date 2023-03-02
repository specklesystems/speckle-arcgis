
from typing import Any, Callable, List, Optional 

from speckle.converter.layers.Layer import VectorLayer, RasterLayer, Layer
from speckle.converter.layers import bimLayerToNative, cadLayerToNative, layerToNative

from specklepy.objects import Base

import arcpy

SPECKLE_TYPES_TO_READ = ["Objects.Geometry.", "Objects.BuiltElements.", "IFC"] # will properly traverse and check for displayValue

def traverseObject(
    base: Base,
    callback: Optional[Callable[[Base, str], bool]],
    check: Optional[Callable[[Base], bool]],
    streamBranch: str,
):
    print("traverse Object")
    print(base)
    if check and check(base):
        res = callback(base, streamBranch) if callback else False
        print(res)
        if res:
            return
    memberNames = base.get_member_names()
    #print(base)
    print(memberNames)
    for name in memberNames:
        try:
            if ["id", "applicationId", "units", "speckle_type"].index(name):
                continue
        except:
            pass
        print(name)
        traverseValue(base[name], callback, check, streamBranch)

def traverseValue(
    value: Any,
    callback: Optional[Callable[[Base, str], bool]],
    check: Optional[Callable[[Base], bool]],
    streamBranch: str,
):
    print("traverse Value")
    print(value)
    if isinstance(value, Base):
        traverseObject(value, callback, check, streamBranch)
    if isinstance(value, List):
        for item in value:
            traverseValue(item, callback, check, streamBranch)

def callback(base: Base, streamBranch: str) -> bool:
    print("callback")
    if isinstance(base, VectorLayer) or isinstance(base, Layer) or isinstance(base, RasterLayer):
        if isinstance(base, Layer):
            arcpy.AddWarning(f"Class \"Layer\" will be deprecated in future updates in favour of \"VectorLayer\" or \"RasterLayer\"") 
        layer = layerToNative(base, streamBranch)
        print(layer)
        if layer is not None:
            arcpy.AddMessage("Layer created: " + layer.name)
    else:
        loopObj(base, "", streamBranch)
    return True

def loopObj(base: Base, baseName: str, streamBranch: str):
    memberNames = base.get_member_names()
    for name in memberNames:
        if name in ["id", "applicationId", "units", "speckle_type"]: continue
        # skip if traversal goes to displayValue of an object, that will be readable anyway:
        if (name == "displayValue" or name == "@displayValue") and base.speckle_type.startswith(tuple(SPECKLE_TYPES_TO_READ)): continue 

        try: loopVal(base[name], baseName + "/" + name, streamBranch)
        except: pass

def loopVal(value: Any, name: str, streamBranch: str): # "name" is the parent object/property/layer name

    if isinstance(value, Base): 
        try: # loop through objects with Speckletype prop, but don't go through parts of Speckle Geometry object
            if not value.speckle_type.startswith("Objects.Geometry."): 
                loopObj(value, name, streamBranch)
        except: 
            loopObj(value, name, streamBranch)

    elif isinstance(value, List):
        streamBranch = streamBranch.replace("[","_").replace("]","_").replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_")

        objectListConverted = 0
        print("loop val - List")
        for i, item in enumerate(value):
            loopVal(item, name, streamBranch)
            if item.speckle_type and item.speckle_type.startswith("IFC"): 
                # keep traversing infinitely, just don't run repeated conversion for the same list of objects
                try: 
                    if item["displayValue"] is not None and objectListConverted == 0: 
                        bimLayerToNative(value, name, streamBranch)
                        objectListConverted += 1
                except: 
                    try: 
                        if item["@displayValue"] is not None and objectListConverted == 0: 
                            bimLayerToNative(value, name, streamBranch)
                            objectListConverted += 1
                    except: pass 
            
            elif item.speckle_type and (item.speckle_type == "Objects.Geometry.Mesh" or item.speckle_type == "Objects.Geometry.Brep" or item.speckle_type.startswith("Objects.BuiltElements.")):
                bimLayerToNative(value, name, streamBranch)
                break
            elif item.speckle_type and item.speckle_type != "Objects.Geometry.Mesh" and item.speckle_type != "Objects.Geometry.Brep" and item.speckle_type.startswith("Objects.Geometry."): # or item.speckle_type == 'Objects.BuiltElements.Alignment'): 
                pt, pl = cadLayerToNative(value, name, streamBranch)
                if pt is not None: arcpy.AddMessage("Layer group created: " + str(pt.name))
                if pl is not None: arcpy.AddMessage("Layer group created: " + str(pl.name))
                break


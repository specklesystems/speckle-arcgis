from typing import Any, List, Union
from specklepy.objects import Base
import arcpy 


def getVariantFromValue(value: Any) -> Union[str, None]:
    # TODO add Base object
    pairs = {
        str: "TEXT", # 10
        float: "FLOAT",
        int: "LONG",
        bool: "SHORT"
        #date: "SHORT"
    }
    t = type(value)
    res = None
    try: res = pairs[t]
    except: pass
    #if isinstance(value, str) and "PyQt5.QtCore.QDate(" in value: res = QVariant.Date #14
    #elif isinstance(value, str) and "PyQt5.QtCore.QDateTime(" in value: res = QVariant.DateTime #16

    return res

def getLayerAttributes(features: List[Base]) -> dict:
    fields = {}
    all_props = []
    for feature in features: 
        #get object properties to add as attributes
        dynamicProps = feature.get_dynamic_member_names()
        attrsToRemove = ['geometry','applicationId','bbox','displayStyle', 'id', 'renderMaterial', 'userDictionary', 'userStrings','geometry']
        for att in attrsToRemove:
            try: dynamicProps.remove(att)
            except: pass

        dynamicProps.sort()

        # add field names and variands 
        #variants = [] 
        for name in dynamicProps:
            if name not in all_props: all_props.append(name)

            value = feature[name]
            variant = getVariantFromValue(value)
            if not variant: variant = None #LongLong #4 

            # add a field if not existing yet AND if variant is known
            if variant and (name not in fields.keys()): 
                fields.update({name: variant})
            
            elif name in fields.keys(): #check if the field was empty previously: 
                #nameIndex = fields.indexFromName(name)
                oldVariant = fields[name]
                #print(oldVariant)
                # replace if new one is NOT LongLong or IS String
                if oldVariant != "TEXT" and variant == "TEXT": 
                    fields.update({name: variant}) 

    # replace all empty ones wit String
    for name in all_props:
        if name not in fields.keys(): 
            fields.update({name: "TEXT"}) 
    #print(fields)
    return fields

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
    arcpy.AddWarning(f"Units {units} are not supported. Meters will be applied by default.")
    return 1.0


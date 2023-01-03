from typing import Dict, Any, List, Union
import json 
from specklepy.objects import Base
import arcpy 

from arcpy._mp import ArcGISProject, Map, Layer as arcLayer
import os

ATTRS_REMOVE = ['geometry','applicationId','bbox','displayStyle', 'id', 'renderMaterial', 'displayMesh', 'displayValue'] 

def getVariantFromValue(value: Any) -> Union[str, None]:
    #print("_________get variant from value_______")
    # TODO add Base object
    pairs = [
        (str, "TEXT"), # 10
        (float, "FLOAT"),
        (int, "LONG"),
        (bool, "SHORT")
        #date: "SHORT"
    ]
    res = None
    for p in pairs:
        if isinstance(value, p[0]): 
            res = p[1]
            try:
                if res == "LONG" and (value>= 2147483647 or value<= -2147483647):
                    #https://pro.arcgis.com/en/pro-app/latest/help/data/geodatabases/overview/arcgis-field-data-types.htm
                    res = "FLOAT"
            except Exception as e: print(e)
            break

    return res

def getLayerAttributes(featuresList: List[Base], attrsToRemove: List[str] = ATTRS_REMOVE ) -> dict[str, str]:
    print("03________ get layer attributes")

    if not isinstance(featuresList, list): features = [featuresList]
    else: features = featuresList[:]
    
    fields = {}
    all_props = []
    for feature in features: 
        #get object properties to add as attributes
        dynamicProps = feature.get_dynamic_member_names()
        for att in attrsToRemove:
            try: dynamicProps.remove(att)
            except: pass
        dynamicProps.sort()

        # add field names and variands 
        for name in dynamicProps:
            #if name not in all_props: all_props.append(name)

            value = feature[name]
            variant = getVariantFromValue(value)
            if not variant: variant = None #LongLong #4 

            # go thought the dictionary object
            if value and isinstance(value, list):
                #all_props.remove(name) # remove generic dict name
                for i, val_item in enumerate(value):
                    newF, newVals = traverseDict( {}, {}, name+"_"+str(i), val_item)

                    for i, (k,v) in enumerate(newF.items()):
                        if k not in all_props: all_props.append(k)
                        if k not in fields.keys(): fields.update({k: v}) 
                        else: #check if the field was empty previously: 
                            oldVariant = fields[k]
                            # replace if new one is NOT Float (too large integers)
                            if oldVariant != "FLOAT" and v == "FLOAT": 
                                fields.update({k: v}) 
                            # replace if new one is NOT LongLong or IS String
                            if oldVariant != "TEXT" and v == "TEXT": 
                                fields.update({k: v}) 
            
            # add a field if not existing yet 
            else: # if str, Base, etc
                newF, newVals = traverseDict( {}, {}, name, value)
                
                for i, (k,v) in enumerate(newF.items()):
                    if k not in all_props: all_props.append(k)
                    if k not in fields.keys(): fields.update({k: v}) #if variant is known
                    else: #check if the field was empty previously: 
                        oldVariant = fields[k]
                        # replace if new one is NOT Float (too large integers)
                        if oldVariant != "FLOAT" and v == "FLOAT": 
                            fields.update({k: v}) 
                        # replace if new one is NOT LongLong or IS String
                        if oldVariant != "TEXT" and v == "TEXT": 
                            fields.update({k: v}) 
                            
    # replace all empty ones wit String
    for name in all_props:
        if name not in fields.keys(): 
            fields.update({name: 'TEXT'}) 

    fields_sorted = {k: v for k, v in sorted(fields.items(), key=lambda item: item[0])}
    return fields_sorted

def traverseDict(newF: dict, newVals: dict, nam: str, val: Any):
    
    if isinstance(val, dict):
        for i, (k,v) in enumerate(val.items()):
            newF, newVals = traverseDict( newF, newVals, nam+"_"+k, v)
    elif isinstance(val, Base):
        dynamicProps = val.get_dynamic_member_names()
        for att in ATTRS_REMOVE:
            try: dynamicProps.remove(att)
            except: pass
        dynamicProps.sort()

        item_dict = {} 
        for prop in dynamicProps:
            item_dict.update({prop: val[prop]})

        for i, (k,v) in enumerate(item_dict.items()):
            newF, newVals = traverseDict( newF, newVals, nam+"_"+k, v)
    else: 
        var = getVariantFromValue(val)
        if var is None: 
            var = 'TEXT'
            val = str(val)
        #print(var)
        newF.update({nam: var})
        newVals.update({nam: val})  

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
    arcpy.AddWarning(f"Units {units} are not supported. Meters will be applied by default.")
    return 1.0

def findTransformation(f_shape, geomType, layer_sr: arcpy.SpatialReference, projectCRS: arcpy.SpatialReference, selectedLayer: arcLayer):
    #apply transformation if needed
    if layer_sr.name != projectCRS.name:
        tr0 = tr1 = tr2 = tr_custom = None
        print(layer_sr)
        try:
            transformations = arcpy.ListTransformations(layer_sr, projectCRS)
            customTransformName = "layer_sr.name"+"_To_"+ projectCRS.name
            if len(transformations) == 0:
                midSr = arcpy.SpatialReference("WGS 1984") # GCS_WGS_1984
                try:
                    tr1 = arcpy.ListTransformations(layer_sr, midSr)[0]
                    tr2 = arcpy.ListTransformations(midSr, projectCRS)[0]
                except: 
                    #customGeoTransfm = "GEOGTRAN[METHOD['Geocentric_Translation'],PARAMETER['X_Axis_Translation',''],PARAMETER['Y_Axis_Translation',''],PARAMETER['Z_Axis_Translation','']]"
                    #CreateCustomGeoTransformation(customTransformName, layer_sr, projectCRS)
                    tr_custom = customTransformName
            else: 
                #print("else")
                # choose equation based instead of file-based/grid-based method, 
                # to be consistent with QGIS: https://desktop.arcgis.com/en/arcmap/latest/map/projections/choosing-an-appropriate-transformation.htm
                selecterTr = {}
                for tr in transformations:
                    if "NTv2" not in tr and "NADCON" not in tr: 
                        set1 = set( layer_sr.name.split("_") + projectCRS.name.split("_") )
                        set2 = set( tr.split("_") )
                        diff = len( set(set1).symmetric_difference(set2) )
                        selecterTr.update({tr: diff})
                selecterTr = dict(sorted(selecterTr.items(), key=lambda item: item[1]))
                tr0 = list(selecterTr.keys())[0]

            if geomType != "Point" and geomType != "Polyline" and geomType != "Polygon" and geomType != "Multipoint":
                try: arcpy.AddWarning("Unsupported or invalid geometry in layer " + selectedLayer.name)
                except: arcpy.AddWarning("Unsupported or invalid geometry")

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
            arcpy.AddWarning(f"Spatial Transformation not found for layer {selectedLayer.name}")
            return None

    return f_shape    

def traverseDictByKey(d: Dict, key:str ="", result = None) -> Dict:
    print("__traverse")

    result = None
    #print(d)
    for k, v in d.items():
        
        try: v = json.loads(v)
        except: pass 
        if isinstance(v, dict):
            #print("__dict__")
            if k == key: print("__break loop"); result = v; return result
            else: 
                result = traverseDictByKey(v, key, result)
                if result is not None: return result
        if isinstance(v, list):
            for item in v: 
                #print(item) 
                if isinstance(item, dict): 
                    result = traverseDictByKey(item, key, result)
                    if result is not None: return result
    #print("__result is: ____________")
    #return result 

def hsv_to_rgb(listHSV):
    h, s, v = listHSV[0], listHSV[1], listHSV[2]
    if s == 0.0: v*=255; return (v, v, v)
    i = int(h*6.) # XXX assume int() truncates!
    f = (h*6.)-i; p,q,t = int(255*(v*(1.-s))), int(255*(v*(1.-s*f))), int(255*(v*(1.-s*(1.-f)))); v*=255; i%=6
    if i == 0: return (v, t, p)
    if i == 1: return (q, v, p)
    if i == 2: return (p, v, t)
    if i == 3: return (p, q, v)
    if i == 4: return (t, p, v)
    if i == 5: return (v, p, q)

def cmyk_to_rgb(c, m, y, k, cmyk_scale, rgb_scale=255):
    r = rgb_scale * (1.0 - c / float(cmyk_scale)) * (1.0 - k / float(cmyk_scale))
    g = rgb_scale * (1.0 - m / float(cmyk_scale)) * (1.0 - k / float(cmyk_scale))
    b = rgb_scale * (1.0 - y / float(cmyk_scale)) * (1.0 - k / float(cmyk_scale))
    return r, g, b

def newLayerGroupAndName(layerName: str, streamBranch: str, project: ArcGISProject) -> str:
    print("___new Layer Group and Name")
    #CREATE A GROUP "received blabla" with sublayers
    layerGroup = None
    newGroupName = f'{streamBranch}'
    print(newGroupName)
    for l in project.activeMap.listLayers():
        if l.longName == newGroupName: layerGroup = l; break 
    
    #find a layer with a matching name in the "latest" group 
    newName = f'{streamBranch.split("_")[len(streamBranch.split("_"))-1]}_{layerName}'

    all_layer_names = []
    layerExists = 0
    for l in project.activeMap.listLayers(): 
        if l.longName.startswith(newGroupName + "\\"):
            all_layer_names.append(l.longName)
    #print(all_layer_names)
    print(newName)

    longName = streamBranch + "\\" + newName 
    if longName in all_layer_names: 
        for index, letter in enumerate('234567890abcdefghijklmnopqrstuvwxyz'):
            if (longName + "_" + letter) not in all_layer_names: 
                newName += "_"+letter 
                layerExists +=1 
                break 
    print(newName)              
    return newName, layerGroup 


def curvedFeatureClassToSegments(layer) -> str:
    print("___densify___")
    data = arcpy.Describe(layer.dataSource)
    dataPath = data.catalogPath
    print(dataPath)
    newPath = dataPath+"_backup"

    arcpy.management.CopyFeatures(dataPath, newPath) # features copied like this do not preserve curved segments

    arcpy.edit.Densify(in_features = newPath, densification_method = "ANGLE", max_angle = 0.01, max_vertex_per_segment = 100) # https://pro.arcgis.com/en/pro-app/latest/tool-reference/editing/densify.htm
    print(newPath)
    return newPath

def validate_path(path: str):
    # https://github.com/EsriOceans/btm/commit/a9c0529485c9b0baa78c1f094372c0f9d83c0aaf
    """If our path contains a DB name, make sure we have a valid DB name and not a standard file name."""
    dirname, file_name = os.path.split(path)
    #print(dirname)
    #print(file_name)
    file_base = os.path.splitext(file_name)[0]
    if dirname == '':
        # a relative path only, relying on the workspace
        dirname = arcpy.env.workspace
    path_ext = os.path.splitext(dirname)[1].lower()
    if path_ext in ['.mdb', '.gdb', '.sde']:
        # we're working in a database
        file_name = arcpy.ValidateTableName(file_base) # e.g. add a letter in front of the name 
    validated_path = os.path.join(dirname, file_name)
    #msg("validated path: %s; (from %s)" % (validated_path, path))
    return validated_path

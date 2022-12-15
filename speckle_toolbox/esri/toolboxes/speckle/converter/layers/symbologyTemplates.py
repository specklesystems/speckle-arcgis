import json
from typing import Any, List, Union
import copy
import os

import arcpy 
from arcpy._mp import ArcGISProject

from speckle.converter.layers.Layer import Layer, VectorLayer, RasterLayer 
from arcpy.management import (CreateFeatureclass, MakeFeatureLayer,
                              AddFields, AlterField, DefineProjection )

def jsonFromLayerStyle(layerArcgis, path_style):
    # write updated renderer to file and get layerStyle variable 
    arcpy.management.SaveToLayerFile(layerArcgis, path_style, False)
    f = open(path_style, "r")
    layerStyle = json.loads(f.read())
    f.close()
    os.remove(path_style)
    return layerStyle


def vectorRendererToNative(project: ArcGISProject, active_map, layerGroup, layerSpeckle: Union[Layer, VectorLayer], layerArcgis, f_class, existingAttrs: List) -> Union[None, dict[str, Any]] :
    print("___________APPLY VECTOR RENDERER______________")
    print(layerArcgis)
    print(f_class)
    renderer = layerSpeckle.renderer 

    if renderer and renderer['type']:
        print(renderer['type'])

        root_path = "\\".join(project.filePath.split("\\")[:-1])
        #path_style = root_path + '\\' + str(f_class).split('\\')[-1] + '_old.lyrx'

        data = arcpy.Describe(layerArcgis.dataSource)
        if layerArcgis.isFeatureLayer:
            geomType = data.shapeType
            sym = layerArcgis.symbology

            if renderer['type'] == 'singleSymbol':
                print("RENDERER SINGLE")
                print(renderer)

                r,g,b = get_r_g_b(renderer['properties']['symbol']['symbColor']) 
                #print(r,g,b)
                #print(sym.renderer.symbol.color)
                sym.renderer.symbol.color = {'RGB': [r, g, b, 100]}
                #print(sym.renderer.symbol.color)
                layerArcgis.symbology = sym # SimpleRenderer
                #print(layerArcgis)
                return layerArcgis 

            elif renderer['type']  == 'categorizedSymbol':
                print("RENDERER CATEGORIZED")
                print(renderer)

                cats = renderer['properties']['categories']
                attribute = renderer['properties']['attribute']
                if attribute not in existingAttrs: return layerArcgis 

                #vl2 = active_map.addLayer(layerArcgis)[0]
                #sym = layerArcgis.symbology
                sym.updateRenderer('UniqueValueRenderer')
                print(sym.renderer.type)
                print(existingAttrs)
                print(attribute)

                sym.renderer.fields = [attribute]
                for k, grp in enumerate(sym.renderer.groups):
                    for itm in grp.items:
                        transVal = itm.values[0][0] #Grab the first "percent" value in the list of potential values
                        for i in range(len(cats)):
                            label = cats[i]['value'] 
                            if label is None or label=="" or str(label)=="": label = "<Null>"
                            r,g,b = get_r_g_b(cats[i]['symbColor']) 

                            if str(transVal) == label:
                                itm.symbol.color = {'RGB': [r, g, b, 100]}
                                itm.label = label
                                break
                layerArcgis.symbology = sym
                return layerArcgis 

            elif renderer['type'] == 'graduatedSymbol': 
                print("RENDERER GRADUATED")
                print(renderer)

                attribute = renderer['properties']['attribute']
                gradMetod = renderer['properties']['gradMethod'] # by color or by size
                if gradMetod  != 0: 
                    r,g,b = get_r_g_b(renderer['properties']['sourceSymbColor'] ) 
                    sym.renderer.symbol.color = {'RGB': [r, g, b, 100]}
                    layerArcgis.symbology = sym # SimpleRenderer
                    return layerArcgis 
                if attribute not in existingAttrs or gradMetod != 0: return layerArcgis # by color, not line width 

                sym.updateRenderer('GraduatedColorsRenderer')
                print(sym.renderer.type)

                r,g,b = get_r_g_b(renderer['properties']['sourceSymbColor']) 
                ramp = renderer['properties']['ramp'] # {discrete, rampType, stops}
                ranges = renderer['properties']['ranges'] # []

                # get all existing values 
                all_values = []
                with arcpy.da.UpdateCursor(f_class, attribute) as cur:
                    for rowShape in cur: 
                        all_values.append(rowShape[0])
                    print(all_values)
                del cur 

                print(len(ranges))
                sym.renderer.classificationField = attribute
                print(sym.renderer.breakCount)
                sym.renderer.breakCount = len(ranges)
                print(sym.renderer.breakCount)
                
                if len(sym.renderer.classBreaks) > 0:
                    totalClasses = 0
                    for k, br in enumerate(ranges):
                        
                        print(totalClasses)
                        if sym.renderer.breakCount < len(ranges):
                            valFits = 0
                            # check if any existing value fits in this range:
                            for val in all_values: 
                                if val <= ranges[k]["upper"] and (totalClasses==0 or (totalClasses>0 and sym.renderer.classBreaks[totalClasses-1].upperBound<val)):
                                    valFits+=1
                                    break
                            if valFits == 0: continue
                            
                        r,g,b = get_r_g_b(ranges[k]['symbColor']) 

                        #classBreak.upperBound = ranges[k]["upper"]
                        sym.renderer.classBreaks[totalClasses].upperBound = ranges[k]["upper"]
                        sym.renderer.classBreaks[totalClasses].label = ranges[k]["label"]
                        sym.renderer.classBreaks[totalClasses].symbol.color = {'RGB': [r, g, b, 100]}
                        totalClasses += 1 

                        #layerArcgis.symbology = sym
                        print(ranges[k]["label"])
                        print(ranges[k]["upper"])

                    sym.renderer.classBreaks[0].upperBound = ranges[0]["upper"] # otherwise its assigned maximum value

                layerArcgis.symbology = sym
                return layerArcgis 

            else: return None 

def get_r_g_b(rgb: int) -> tuple[int, int, int]:
    r = g = b = 0
    try: 
        r = (rgb & 0xFF0000) >> 16
        g = (rgb & 0xFF00) >> 8
        b = rgb & 0xFF 
    except: r = g = b = 0
    
    r,g,b = check_rgb(r,g,b)
    return r,g,b 

def check_rgb(r:int, g:int, b:int) -> tuple[int, int, int]:

    if not isinstance(r, int) or r<0 or r>255: r=g=b=0
    if not isinstance(g, int) or g<0 or g>255: r=g=b=0
    if not isinstance(b, int) or b<0 or b>255: r=g=b=0
    return r,g,b 

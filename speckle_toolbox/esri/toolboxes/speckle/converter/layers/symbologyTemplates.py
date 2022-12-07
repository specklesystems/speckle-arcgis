import json
from typing import Any, List, Union
import copy
import os

import arcpy 
from arcpy._mp import ArcGISProject

from speckle.converter.layers.Layer import Layer, VectorLayer, RasterLayer 
import unittest 

def vectorRendererToNative(project: ArcGISProject, active_map, layerGroup, layerSpeckle: Union[Layer, VectorLayer], layerArcgis, f_class, existingAttrs: List) -> Union[None, dict[str, Any]] :
    print("___________APPLY VECTOR RENDERER______________")
    print(layerArcgis)
    print(f_class)
    #for layer in active_map.listLayers(): 
    #    if layer.longName == layerGroup.name + '\\' + layerArcgis.longName:
    #        layerArcgis = layer
    #        break

    #for layer in active_map.listLayers(): 
    #    if layer.isFeatureLayer or layer.isRasterLayer: 
    #            all_layers.append(layer)

    renderer = layerSpeckle.renderer 
    layerStyle = None 

    if renderer and renderer['type']:
        print(renderer['type'])

        root_path = "\\".join(project.filePath.split("\\")[:-1])
        path_style = root_path + '\\layer_speckle_symbology.lyrx'
        path_style2 = root_path + '\\layer_speckle_symbology2.lyrx'
        rendererNew = None 

        data = arcpy.Describe(layerArcgis.dataSource)
        if layerArcgis.isFeatureLayer:
            geomType = data.shapeType
            sym = layerArcgis.symbology
            #print(sym.renderer.type)

            

            if renderer['type'] == 'singleSymbol':
                print("RENDERER SINGLE")

                # write updated renderer to file and get layerStyle variable 
                arcpy.management.SaveToLayerFile(layerArcgis, path_style, False)
                f = open(path_style, "r")
                layerStyle = json.loads(f.read())
                f.close()
                os.remove(path_style)

                if geomType =="Polygon": print(layerStyle["layerDefinitions"][0]["renderer"])
                r,g,b = get_r_g_b(renderer['properties']['symbol']['symbColor']) 
                rendererNew = get_polygon_simpleRenderer(geomType,r,g,b)
                print(rendererNew)

            elif renderer['type']  == 'categorizedSymbol':
                print("RENDERER CATEGORIZED")
                sym.updateRenderer('UniqueValueRenderer')
                layerArcgis.symbology = sym
                print(sym.renderer.type)

                # write updated renderer to file and get layerStyle variable 
                arcpy.management.SaveToLayerFile(layerArcgis, path_style, False)
                f = open(path_style, "r")
                layerStyle = json.loads(f.read())
                f.close()
                os.remove(path_style)

                if geomType =="Polygon": print(layerStyle["layerDefinitions"][0]["renderer"])
                #r,g,b = get_r_g_b(renderer['properties']['sourceSymbColor'])

                cats = renderer['properties']['categories']

                attribute = renderer['properties']['attribute']
                print(attribute)
                print(existingAttrs)
                if attribute not in existingAttrs: return 

                categories = []
                noneVal = 0

                rendererNew = get_polygon_uniqueValues(geomType,attribute, cats)  
                print(rendererNew)

            elif renderer['type'] == 'graduatedSymbol': 
                print("RENDERER GRADUATED")
                sym.updateRenderer('GraduatedColorsRenderer')

                attribute = renderer['properties']['attribute']
                gradMetod = renderer['properties']['gradMethod'] # by color or by size
                if attribute not in existingAttrs or gradMetod != 0: return # by color, not line width 

                print(attribute)
                print(existingAttrs)

                r,g,b = get_r_g_b(renderer['properties']['sourceSymbColor']) 
                ramp = renderer['properties']['ramp'] # {discrete, rampType, stops}
                ranges = renderer['properties']['ranges'] # []

                sym.renderer.classificationField = attribute
                sym.renderer.breakCount = len(ranges)
                layerArcgis.symbology = sym
                print(sym.renderer.type)

                # write updated renderer to file and get layerStyle variable 
                arcpy.management.SaveToLayerFile(layerArcgis, path_style, False)
                f = open(path_style, "r")
                layerStyle = json.loads(f.read())
                f.close()
                os.remove(path_style)

                if geomType =="Polygon": 
                    print(layerStyle["layerDefinitions"][0]["renderer"])
                    rendererNew = get_polygon_graduated(geomType, attribute, ranges)
                    print(rendererNew)
            else: return 

            if geomType =="Polygon" and rendererNew is not None:
                layerStyle["layerDefinitions"][0]["renderer"] = rendererNew
                f = open(path_style2, "w")
                f.write(json.dumps(layerStyle, indent=4).replace(": True,", ": true,") )
                f.close()
                print("MODIFIED LAYER STYLE")
                print(layerArcgis.dataSource)
                try:
                    arcpy.ApplySymbologyFromLayer_management(
                        in_layer=layerArcgis.dataSource, 
                        in_symbology_layer=path_style2, 
                        update_symbology='UPDATE')
                except Exception as e: arcpy.AddMessage(e); print(e)
                #os.remove(path_style2)


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

COLOR_RAMP_GRAD_POLYGON = {
    "type" : "CIMMultipartColorRamp",
    "colorRamps" : [
    {
        "type" : "CIMPolarContinuousColorRamp",
        "colorSpace" : {
        "type" : "CIMICCColorSpace",
        "url" : "Default RGB"
        },
        "fromColor" : {
        "type" : "CIMRGBColor",
        "values" : [115,255,223,100]
        },
        "toColor" : {
        "type" : "CIMRGBColor",
        "values" : [169,0,230,100]
        },
        "interpolationSpace" : "HSV",
        "polarDirection" : "Clockwise"
    }
    ],
    "weights" : [1]
        
}

UNIQUE_VALUE_POLYGON_RENDERER = {
    "type" : "CIMUniqueValueRenderer",
    "colorRamp" : {
        "type" : "CIMRandomHSVColorRamp",
        "colorSpace" : {
        "type" : "CIMICCColorSpace",
        "url" : "Default RGB"
        },
        "maxH" : 360,
        "minS" : 15,
        "maxS" : 30,
        "minV" : 99,
        "maxV" : 100,
        "minAlpha" : 100,
        "maxAlpha" : 100
    },
    "defaultLabel" : "<all other values>",
    "defaultSymbol" : {
        "type" : "CIMSymbolReference",
        "symbol" : {
        "type" : "CIMPolygonSymbol",
        "symbolLayers" : [
            {
            "type" : "CIMSolidStroke",
            "enable" : True,
            "capStyle" : "Round",
            "joinStyle" : "Round",
            "lineStyle3D" : "Strip",
            "miterLimit" : 10,
            "width" : 0.69999999999999996,
            "color" : {
                "type" : "CIMRGBColor",
                "values" : [110,110,110,100]
            }
            },
            {
            "type" : "CIMSolidFill",
            "enable" : True,
            "color" : {
                "type" : "CIMRGBColor",
                "values" : [130,130,130,100]
            }
            }
        ]
        }
    },
    "defaultSymbolPatch" : "Default",
    "fields" : [""],
    "groups" : [],
    "useDefaultSymbol" : True,
    "polygonSymbolColorTarget" : "Fill"
    }

GRADUATED_POLYGON_RENDERER = {
    "type" : "CIMClassBreaksRenderer",
    "barrierWeight" : "High",
    "breaks" : [
        {
            "type" : "CIMClassBreak",
            "label" : "0.002448 - 0.002871",
            "patch" : "Default",
            "symbol" : {
            "type" : "CIMSymbolReference",
            "symbol" : {
                "type" : "CIMPolygonSymbol",
                "symbolLayers" : [
                {
                    "type" : "CIMSolidStroke",
                    "enable" : True,
                    "capStyle" : "Round",
                    "joinStyle" : "Round",
                    "lineStyle3D" : "Strip",
                    "miterLimit" : 10,
                    "width" : 0.69999999999999996,
                    "color" : {
                    "type" : "CIMRGBColor",
                    "values" : [110,110,110,100]
                    }
                },
                {
                    "type" : "CIMSolidFill",
                    "enable" : True,
                    "color" : {
                    "type" : "CIMHSVColor",
                    "values" : [0,100,96,100]
                    }
                }
                ]
            }
            },
            "upperBound" : 0.0028705696302367464
        }
    ],
    "classBreakType" : "GraduatedColor",
    "classificationMethod" : "NaturalBreaks",
    "colorRamp" : {
        "type" : "CIMPolarContinuousColorRamp",
        "colorSpace" : {
        "type" : "CIMICCColorSpace",
        "url" : "Default RGB"
        },
        "fromColor" : {
            "type" : "CIMHSVColor",
            "values" : [60,100,96,100]
        },
        "toColor" : {
            "type" : "CIMHSVColor",
            "values" : [0,100,96,100]
        },
        "interpolationSpace" : "HSV",
        "polarDirection" : "Auto"
    },
    "field" : "",
    "minimumBreak" : 0.0010476396428161403,
    "numberFormat" : {
        "type" : "CIMNumericFormat",
        "alignmentOption" : "esriAlignLeft",
        "alignmentWidth" : 0,
        "roundingOption" : "esriRoundNumberOfDecimals",
        "roundingValue" : 6,
        "zeroPad" : True
    },
    "showInAscendingOrder" : True,
    "heading" : "",
    "sampleSize" : 10000,
    "defaultSymbolPatch" : "Default",
    "defaultSymbol" : {
        "type" : "CIMSymbolReference",
        "symbol" : {
        "type" : "CIMPolygonSymbol",
        "symbolLayers" : [
            {
            "type" : "CIMSolidStroke",
            "enable" : True,
            "capStyle" : "Round",
            "joinStyle" : "Round",
            "lineStyle3D" : "Strip",
            "miterLimit" : 10,
            "width" : 0.69999999999999996,
            "color" : {
                "type" : "CIMRGBColor",
                "values" : [110,110,110,100]
            }
            },
            {
            "type" : "CIMSolidFill",
            "enable" : True,
            "color" : {
                "type" : "CIMRGBColor",
                "values" : [130,130,130,100]
            }
            }
        ]
        }
    },
    "defaultLabel" : "<out of range>",
    "polygonSymbolColorTarget" : "Fill",
    "normalizationType" : "Nothing",
    "exclusionLabel" : "<excluded>",
    "exclusionSymbol" : {
        "type" : "CIMSymbolReference",
        "symbol" : {
        "type" : "CIMPolygonSymbol",
        "symbolLayers" : [
            {
            "type" : "CIMSolidStroke",
            "enable" : True,
            "capStyle" : "Round",
            "joinStyle" : "Round",
            "lineStyle3D" : "Strip",
            "miterLimit" : 10,
            "width" : 0.69999999999999996,
            "color" : {
                "type" : "CIMRGBColor",
                "values" : [110,110,110,100]
            }
            },
            {
            "type" : "CIMSolidFill",
            "enable" : True,
            "color" : {
                "type" : "CIMRGBColor",
                "values" : [255,0,0,100]
            }
            }
        ]
        }
    },
    "useExclusionSymbol" : False,
    "exclusionSymbolPatch" : "Default"
    }

def get_polygon_simpleRenderer(geomType:str, r:int, g:int, b:int) -> dict[str,Any]:
          
    if geomType == "Polyline": return None
    if geomType == "Point": return None
    if geomType == "Multipoint": return None

    if geomType == "Polygon": 
        return {
            "type" : "CIMSimpleRenderer",
            "patch" : "Default",
            "symbol" : {
            "type" : "CIMSymbolReference",
            "symbol" : {
                "type" : "CIMPolygonSymbol",
                "symbolLayers" : [
                {
                    "type" : "CIMSolidStroke",
                    "enable" : True,
                    "name" : "Group 1",
                    "capStyle" : "Round",
                    "joinStyle" : "Round",
                    "lineStyle3D" : "Strip",
                    "miterLimit" : 10,
                    "width" : 0.69999999999999996,
                    "color" : {
                    "type" : "CIMRGBColor",
                    "values" : [110, 110, 110,100]
                    }
                },
                {
                    "type" : "CIMSolidFill",
                    "enable" : True,
                    "name" : "Group 2",
                    "color" : {
                    "type" : "CIMRGBColor",
                    "values" : [r,g,b,100]
                    }
                }
                ]
            }
            }
        }

def get_polygon_uniqueValues(geomType:str, attribute: str, cats: List[dict]) -> dict [str, Any]:
    
    new_renderer = copy.deepcopy(UNIQUE_VALUE_POLYGON_RENDERER) 
    new_renderer["fields"] = [attribute]

    if geomType == "Polyline": return None
    if geomType == "Point": return None
    if geomType == "Multipoint": return None

    if geomType == "Polygon": 

        for i in range(len(cats)):
            label = cats[i]['value'] 
            if label is None or label=="": v = "<Null>"

            r,g,b = get_r_g_b(cats[i]['symbColor']) 
            
            new_group = {
                "type" : "CIMUniqueValueGroup",
                "classes" : [
                {
                    "type" : "CIMUniqueValueClass",
                    "label" : label,
                    "patch" : "Default",
                    "symbol" : {
                    "type" : "CIMSymbolReference",
                    "symbol" : {
                        "type" : "CIMPolygonSymbol",
                        "symbolLayers" : [
                        {
                            "type" : "CIMSolidStroke",
                            "enable" : True,
                            "capStyle" : "Round",
                            "joinStyle" : "Round",
                            "lineStyle3D" : "Strip",
                            "miterLimit" : 10,
                            "width" : 0.69999999999999996,
                            "color" : {
                            "type" : "CIMRGBColor",
                            "values" : [110,110,110,100]
                            }
                        },
                        {
                            "type" : "CIMSolidFill",
                            "enable" : True,
                            "color" : {
                            "type" : "CIMHSVColor",
                            "values" : [r,g,b]
                            }
                        }
                        ]
                    }
                    },
                    "values" : [
                    {
                        "type" : "CIMUniqueValue",
                        "fieldValues" : [label]
                    }
                    ],
                    "visible" : True
                }
                ]
            }
            new_renderer["groups"].append(new_group)

    return new_renderer 

def get_polygon_graduated(geomType:str, attribute: str, ranges: List[dict]) -> dict[str, Any]:
    new_renderer = copy.deepcopy(GRADUATED_POLYGON_RENDERER) 
    new_renderer["heading"] = attribute
    new_renderer["breaks"] = []

    newColorRamp = copy.deepcopy(COLOR_RAMP_GRAD_POLYGON)

    if geomType == "Polyline": return None
    if geomType == "Point": return None
    if geomType == "Multipoint": return None

    if geomType == "Polygon": 

        for i, range in enumerate(ranges): 
            r,g,b = get_r_g_b(range['symbColor']) 
            cmin = range['lower']
            cmax = range['upper']
            label = f"{cmin} - {cmax}"
            if i==0: 
                newColorRamp["colorRamps"][0]["fromColor"]["values"] = [r,g,b,100]
                label = str(cmax)
            if i==len(ranges)-1: 
                newColorRamp["colorRamps"][0]["toColor"]["values"] = [r,g,b,100]

            new_category = {
                "type" : "CIMClassBreak",
                "label" : label,
                "patch" : "Default",
                "symbol" : {
                "type" : "CIMSymbolReference",
                "symbol" : {
                    "type" : "CIMPolygonSymbol",
                    "symbolLayers" : [
                    {
                        "type" : "CIMSolidStroke",
                        "enable" : True,
                        "capStyle" : "Round",
                        "joinStyle" : "Round",
                        "lineStyle3D" : "Strip",
                        "miterLimit" : 10,
                        "width" : 0.69999999999999996,
                        "color" : {
                        "type" : "CIMRGBColor",
                        "values" : [110,110,110,100]
                        }
                    },
                    {
                        "type" : "CIMSolidFill",
                        "enable" : True,
                        "color" : {
                        "type" : "CIMHSVColor",
                        "values" : [r,g,b,100]
                        }
                    }
                    ]
                }
                },
                "upperBound" : cmax 
            }
            new_renderer["breaks"].append(new_category)
    
    new_renderer.update({"colorRamp" : newColorRamp}) 

    return new_renderer



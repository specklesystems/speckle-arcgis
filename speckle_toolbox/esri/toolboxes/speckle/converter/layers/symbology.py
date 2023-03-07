import json
from typing import Any, List, Tuple, Union
import copy
import os

from typing import Dict

import arcpy 
from arcpy._mp import ArcGISProject, Layer as arcLayer
from arcpy.management import (CreateFeatureclass, MakeFeatureLayer,
                              AddFields, AlterField, DefineProjection )

from specklepy.objects import Base
from specklepy.objects.other import RenderMaterial

try:
    from speckle.converter.layers.Layer import Layer, VectorLayer, RasterLayer 
except:
    from speckle_toolbox.esri.toolboxes.speckle.converter.layers.Layer import Layer, VectorLayer, RasterLayer 

def jsonFromLayerStyle(layerArcgis, path_style):
    # write updated renderer to file and get layerStyle variable 
    arcpy.management.SaveToLayerFile(layerArcgis, path_style, False)
    f = open(path_style, "r")
    layerStyle = json.loads(f.read())
    f.close()
    os.remove(path_style)
    return layerStyle

def symbol_color_to_speckle(color: dict):
    newColor = (0<<16) + (0<<8) + 0
    try: 
        r = int(color['RGB'][0])
        g = int(color['RGB'][1])
        b = int(color['RGB'][2])
        newColor = (r<<16) + (g<<8) + b
    except: pass 
    return newColor


def colorFromRenderMaterial(material):

    color = {'RGB': [245, 245, 245, 100]} #Objects.Other.RenderMaterial
    if material is not None:
        try: 
            rgb = material.diffuse
            r = (rgb & 0xFF0000) >> 16
            g = (rgb & 0xFF00) >> 8
            b = rgb & 0xFF 
            color = {'RGB': [r, g, b, 100]}
            #print(color)
        except: pass
    return color

def cadBimRendererToNative(project: ArcGISProject, active_map, layerGroup, fetColors: List[RenderMaterial], layerArcgis, f_class, existingAttrs: List) -> Union[None, Dict[str, Any]] :
    print("___________APPLY VECTOR RENDERER______________")
    print(layerArcgis)
    print(f_class)
    print(fetColors)

    attribute = "Speckle_ID"
    root_path = "\\".join(project.filePath.split("\\")[:-1])
    #path_style = root_path + '\\' + str(f_class).split('\\')[-1] + '_old.lyrx'

    data = arcpy.Describe(layerArcgis.dataSource)
    if layerArcgis.isFeatureLayer:
        geomType = data.shapeType
        sym = layerArcgis.symbology

        cursor = arcpy.da.SearchCursor(f_class, attribute)
        class_shapes = [shp_id[0] for n, shp_id in enumerate(cursor)]
        del cursor 

        sym.updateRenderer('UniqueValueRenderer')
        print(sym.renderer.type)
        print(existingAttrs)
        print(attribute)

        sym.renderer.fields = [attribute]
        for k, grp in enumerate(sym.renderer.groups):
            for itm in grp.items:
                transVal = itm.values[0][0] #Grab the first "percent" value in the list of potential values 
                #print(transVal)
                for i in range(len(class_shapes)):
                    label = class_shapes[i]
                    #print(label)
                    if label is None or label=="" or str(label)=="": label = "<Null>"

                    if str(transVal) == label:
                        print("found label")
                        material = fetColors[i]
                        #print(material)
                        itm.symbol.color = colorFromRenderMaterial(material) 
                        itm.label = label
                        break
        layerArcgis.symbology = sym
        #print(layerArcgis)
        return layerArcgis 


def vectorRendererToNative(project: ArcGISProject, active_map, layerGroup, layerSpeckle: Union[Layer, VectorLayer], layerArcgis, f_class, existingAttrs: List) -> Union[None, Dict[str, Any]] :
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

                r,g,b = get_rgb_from_speckle(renderer['properties']['symbol']['symbColor']) 
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
                            r,g,b = get_rgb_from_speckle(cats[i]['symbColor']) 

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
                    r,g,b = get_rgb_from_speckle(renderer['properties']['sourceSymbColor'] ) 
                    sym.renderer.symbol.color = {'RGB': [r, g, b, 100]}
                    layerArcgis.symbology = sym # SimpleRenderer
                    return layerArcgis 
                if attribute not in existingAttrs or gradMetod != 0: return layerArcgis # by color, not line width 

                sym.updateRenderer('GraduatedColorsRenderer')
                print(sym.renderer.type)

                r,g,b = get_rgb_from_speckle(renderer['properties']['sourceSymbColor']) 
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
                            
                        r,g,b = get_rgb_from_speckle(ranges[k]['symbColor']) 

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

def get_rgb_from_speckle(rgb: int) -> Tuple[int, int, int]:
    r = g = b = 0
    try: 
        r = (rgb & 0xFF0000) >> 16
        g = (rgb & 0xFF00) >> 8
        b = rgb & 0xFF 
    except: r = g = b = 0
    
    r,g,b = check_rgb(r,g,b)
    return r,g,b 

def check_rgb(r:int, g:int, b:int) -> Tuple[int, int, int]:

    if not isinstance(r, int) or r<0 or r>255: r=g=b=0
    if not isinstance(g, int) or g<0 or g>255: r=g=b=0
    if not isinstance(b, int) or b<0 or b>255: r=g=b=0
    return r,g,b 



def rasterRendererToNative(project: ArcGISProject, active_map, layerGroup,  layer: RasterLayer, arcLayer, rasterPathsToMerge, newName):
    print("_____rasterRenderer ToNative______")
    renderer = layer.renderer
    rendererNew = None
    print(renderer)

    feat = layer.features[0]
    print(feat)

    bandNames = feat["Band names"]
    print(bandNames)

    sym = arcLayer.symbology
    symJson = None
    path_style = ""
    path_style2 = ""

    print(sym)

    if renderer and renderer['type']:
        
        if not hasattr(arcLayer.symbology, 'colorizer'): 
            # multiband raster, CIMRasterRGBColorizer 
            # arcpy doesnt support multiband raster symbology: https://community.esri.com/t5/arcgis-api-for-python-questions/why-does-arcpy-mp-arcgis-pro-2-6-mosaic-dataset/td-p/1016312 
            root_path = "\\".join(project.filePath.split("\\")[:-1])
            if not os.path.exists(root_path + '\\Layers_Speckle\\raster_bands'): os.makedirs(root_path + '\\Layers_Speckle\\raster_bands')
            path_style = root_path + '\\Layers_Speckle\\raster_bands\\' + newName + '_old.lyrx'
            path_style2 = root_path + '\\Layers_Speckle\\raster_bands\\' + newName + '_new.lyrx'
            symJson = jsonFromLayerStyle(arcLayer, path_style)

        if renderer['type']  == 'singlebandgray':
            print("Singleband grey")
            band_index = renderer['properties']['band']-1
            if symJson is None:
                sym.updateColorizer('RasterStretchColorizer')
                sym.colorizer.band = band_index
                arcLayer.symbology = sym
            else: 
                temp = arcpy.management.MakeRasterLayer(rasterPathsToMerge[band_index], newName + "_temp").getOutput(0)
                active_map.addLayerToGroup(layerGroup, temp)
                temp_layer = None
                for l in active_map.listLayers(): 
                    if l.longName == layerGroup.longName + "\\" + newName + "_temp":
                        print(l.longName)
                        temp_layer = l 
                        break

                sym = temp_layer.symbology
                sym.updateColorizer('RasterStretchColorizer')
                sym.colorizer.band = band_index
                arcLayer.symbology = sym

                active_map.removeLayer(temp_layer) 
                

        elif renderer['type']  == 'multibandcolor':
            print("Multiband")
            if symJson is None: 
                sym.updateColorizer('RasterStretchColorizer')
                arcLayer.symbology = sym 
            else:
                
                redSt =  copy.deepcopy(symJson["layerDefinitions"][0]["colorizer"]["stretchStatsRed"])
                greenSt =  copy.deepcopy(symJson["layerDefinitions"][0]["colorizer"]["stretchStatsGreen"])
                blueSt =  copy.deepcopy(symJson["layerDefinitions"][0]["colorizer"]["stretchStatsBlue"])

                redBand = renderer['properties']['redBand']
                greenBand = renderer['properties']['greenBand']
                blueBand = renderer['properties']['blueBand']
                try: symJson["layerDefinitions"][0]["colorizer"]["greenBandIndex"] = greenBand-1
                except: symJson["layerDefinitions"][0]["colorizer"]["greenBandIndex"] = 0

                try: symJson["layerDefinitions"][0]["colorizer"]["redBandIndex"] = redBand-1
                except: symJson["layerDefinitions"][0]["colorizer"]["redBandIndex"] = 0
                
                try: symJson["layerDefinitions"][0]["colorizer"]["blueBandIndex"] = blueBand-1
                except: symJson["layerDefinitions"][0]["colorizer"]["blueBandIndex"] = 0
                
                print(symJson)
                f = open(path_style2, "w")
                f.write(json.dumps(symJson, indent=2))
                f.close()

                active_map.removeLayer(arcLayer) 
                lyrFile = arcpy.mp.LayerFile(path_style2)
                active_map.addLayerToGroup(layerGroup, lyrFile )
                
                os.remove(path_style2) 

        elif renderer['type']  == 'paletted':
            print("Paletted")
            band_index = renderer['properties']['band']-1

            if symJson is None:
                for br in sym.colorizer.groups:
                    print(br.heading) #"Value"
                    # go through all values classified 
                    for k, itm in enumerate(br.items):
                        if k< len(renderer['properties']['classes']):
                            #go through saved renderer classes
                            for n, cl in enumerate(renderer['properties']['classes']):
                                if k == n:
                                    r,g,b = get_rgb_from_speckle(cl['color']) 
                                    itm.color = {'RGB': [r,g,b, 100]}
                                    itm.label = cl['label']
                                    itm.values = cl['value']
                        else: pass
                arcLayer.symbology = sym 
        else: 
            sym.updateColorizer('RasterStretchColorizer')
            arcLayer.symbology = sym
    return arcLayer
    

def rendererToSpeckle(project: ArcGISProject, active_map, arcLayer, rasterFeat: Base):
    print("_____renderer To Speckle______")
    if arcLayer.isRasterLayer: 
        try: 
            rType = arcLayer.symbology.colorizer.type # 'singleSymbol','categorizedSymbol','graduatedSymbol',
            if rType =='RasterStretchColorizer':  rType = 'singlebandgray'
            elif rType =='RasterUniqueValueColorizer':  rType = 'paletted' # only for 1-band raster 
            else: rType = 'singlebandgray'
        except: 
            rType = "multibandcolor"
            root_path = "\\".join(project.filePath.split("\\")[:-1])
            if not os.path.exists(root_path + '\\Layers_Speckle\\raster_bands'): os.makedirs(root_path + '\\Layers_Speckle\\raster_bands')
            path_style = root_path + '\\Layers_Speckle\\raster_bands\\' + arcLayer.name + '_temp.lyrx'
            #path_style2 = root_path + '\\' + newName + '_new.lyrx'
            symJson = jsonFromLayerStyle(arcLayer, path_style)

        layerRenderer: Dict[str, Any] = {}
        layerRenderer['type'] = rType
        print(rType)
        my_raster = arcpy.Raster(arcLayer.dataSource)  
        rasterBandNames = my_raster.bandNames
        
        #bandNames = rasterFeat["Band names"]
        bandValues = [rasterFeat["@(10000)" + name + "_values"] for name in rasterBandNames]

        if rType == "singlebandgray":  
            try: band = arcLayer.symbology.colorizer.band 
            except: band = 0 
            try: 
                bVals = bandValues[band]
                bvalMin = min(bVals)
                bvalMax = max(bVals)
            except: 
                bvalMin = 0
                bvalMax = 255
            layerRenderer.update({'properties': {'max':bvalMax,'min':bvalMin,'band':band+1,'contrast':1}}) 

        elif rType == "multibandcolor":

            try: greenBand = symJson["layerDefinitions"][0]["colorizer"]["greenBandIndex"] +1
            except: greenBand = None
            try: blueBand = symJson["layerDefinitions"][0]["colorizer"]["blueBandIndex"] +1
            except: blueBand = None
            try: redBand = symJson["layerDefinitions"][0]["colorizer"]["redBandIndex"] +1
            except: 
                print(greenBand)
                print(blueBand)
                if blueBand!=1 and greenBand!=1: redBand= 1
                else: redBand = None
            print(redBand)

            try: 
                rbVals = bandValues[redBand-1]
                rbvalMin = min(rbVals)
                rbvalMax = max(rbVals)
                print(rbvalMin)
                print(rbvalMax)
            except: 
                rbvalMin = 0
                rbvalMax = 255
            try: 
                gbVals = bandValues[greenBand-1]
                gbvalMin = min(gbVals)
                gbvalMax = max(gbVals)
            except: 
                gbvalMin = 0
                gbvalMax = 255
            try: 
                bbVals = bandValues[blueBand-1]
                bbvalMin = min(bbVals)
                bbvalMax = max(bbVals) 
            except: 
                bbvalMin = 0
                bbvalMax = 255

            layerRenderer.update({'properties': {'greenBand':greenBand,'blueBand':blueBand,'redBand':redBand}})
            layerRenderer['properties'].update({'redContrast':1,'redMin':rbvalMin,'redMax':rbvalMax})
            layerRenderer['properties'].update({'greenContrast':1,'greenMin':gbvalMin,'greenMax':gbvalMax})
            layerRenderer['properties'].update({'blueContrast':1,'blueMin':bbvalMin,'blueMax':bbvalMax})
        elif rType == "paletted":  
            band = 0 
            rendererClasses = arcLayer.symbology.colorizer.groups
            classes = []
            sourceRamp = {}

            for i, cl in enumerate(rendererClasses):
                if cl.heading == 'Value':
                    for k, itm in enumerate(cl.items):
                        value = itm.values[0]
                        label = itm.label 
                        try: 
                            r,g,b = itm.color['RGB'][0], itm.color['RGB'][1], itm.color['RGB'][2]
                            sColor = (r<<16) + (g<<8) + b
                            classes.append({'color':sColor,'value':value,'label':label})
                        except: pass 
            layerRenderer.update({'properties': {'classes':classes,'ramp':sourceRamp,'band':band+1}})

        return layerRenderer 
    elif arcLayer.isFeatureLayer: 
        layerRenderer: Dict[str, Any] = {}

        sym = arcLayer.symbology
        print(sym.renderer.type)

        if sym.renderer.type == 'SimpleRenderer':
            layerRenderer['type'] = 'singleSymbol'
            layerRenderer['properties'] = {'symbol':{}, 'symbType':""}
            symbolColor = symbol_color_to_speckle(sym.renderer.symbol.color)
            layerRenderer['properties'].update({'symbol':{'symbColor': symbolColor}, 'symbType':''})

        elif sym.renderer.type == 'UniqueValueRenderer':
            layerRenderer['type'] = 'categorizedSymbol'
            layerRenderer['properties'] = {'attribute': '', 'symbType': ''} #{'symbol':{}, 'ramp':{}, 'ranges':{}, 'gradMethod':"", 'symbType':"", 'legendClassificationAttribute': ""}
            
            attribute = sym.renderer.fields[0]
            layerRenderer['properties']['attribute'] = attribute
            sourceSymbColor = symbol_color_to_speckle(sym.renderer.defaultSymbol.color)
            layerRenderer['properties'].update( {'sourceSymbColor': sourceSymbColor} )
 
            categories = sym.renderer.groups
            layerRenderer['properties']['categories'] = []

            for i, grp in enumerate(categories):
                for itm in grp.items:
                    value = itm.values[0][0]
                    symbColor = symbol_color_to_speckle(itm.symbol.color)
                    label = itm.label
                    layerRenderer['properties']['categories'].append({'value':value,'symbColor':symbColor,'symbOpacity':1, 'sourceSymbColor': sourceSymbColor,'label':label})

        elif sym.renderer.type == 'GraduatedColorsRenderer' or sym.renderer.type == 'GraduatedSymbolsRenderer':
            layerRenderer['type'] = 'graduatedSymbol'
            layerRenderer['properties'] = {'symbol':{}, 'ramp':{}, 'ranges':{}, 'gradMethod':"", 'symbType':""}
        
            attribute = sym.renderer.classificationField 
            sourceSymbColor = (0<<16) + (0<<8) + 0  
            layerRenderer['properties'].update( {'attribute': attribute, 'symbType': '', 'gradMethod': 0, 'sourceSymbColor': sourceSymbColor} )

            rRamp = sym.renderer.colorRamp # QgsGradientColorRamp
            layerRenderer['properties']['ramp'] = {} # gradientColorRampToSpeckle(rRamp)

            rRanges = sym.renderer.classBreaks
            layerRenderer['properties']['ranges'] = []
            for itm in rRanges:
                try: lower = float(itm.label.split(" - ")[0]) if (" - " in rRanges.label) else float(rRanges.label[0])
                except: lower = 0
                upper = itm.upperBound
                symbColor = symbol_color_to_speckle(itm.symbol.color) 
                label = itm.label
                width = 0.26
                # {'label': '1 - 1.4', 'lower': 1.0, 'symbColor': <PyQt5.QtGui.QColor ...BD9B9D4A0>, 'symbOpacity': 1.0, 'upper': 1.4}
                layerRenderer['properties']['ranges'].append({'lower':lower,'upper':upper,'symbColor':symbColor,'symbOpacity':1,'label':label,'width':width})
     
        elif sym.renderer.type == 'UnclassedColorsRenderer':
            layerRenderer['type'] = 'graduatedSymbol'
            layerRenderer['properties'] = {'symbol':{}, 'ramp':{}, 'ranges':{}, 'gradMethod':"", 'symbType':""}
        
            attribute = sym.renderer.field 
            sourceSymbColor = (0<<16) + (0<<8) + 0  
            layerRenderer['properties'].update( {'attribute': attribute, 'symbType': '', 'gradMethod': 0, 'sourceSymbColor': sourceSymbColor} )
            layerRenderer['properties']['ramp'] = {} # gradientColorRampToSpeckle(rRamp)

            lowest = sym.renderer.lowerLabel
            highest = sym.renderer.upperLabel

            # trick to get colors 
            rRamp = sym.renderer.colorRamp # QgsGradientColorRamp
            arcRamp = project.listColorRamps('White to Black')[0]
            sym.updateRenderer('GraduatedColorsRenderer')
            sym.renderer.colorRamp = arcRamp
            sym.renderer.classificationField = attribute
            rows_attributes = arcpy.da.SearchCursor(arcLayer.dataSource, attribute)
            row_attrs = []
            row_max = -1000000000
            row_min = 1000000000
            for k, attrs in enumerate(rows_attributes): 
                row_attrs.append(attrs[0])
                if attrs[0] < row_min: row_min = attrs[0]
                if attrs[0] > row_max: row_max = attrs[0]
            row_range = row_max - row_min
            breakCount = len(list(set(row_attrs))) # only unique values 
            sym.renderer.breakCount = breakCount

            # run as gradient colors 
            rRanges = sym.renderer.classBreaks
            layerRenderer['properties']['ranges'] = []
            for itm in rRanges:
                try: lower = float(itm.label.split(" - ")[0]) if (" - " in rRanges.label) else float(rRanges.label[0])
                except: lower = 0
                upper = itm.upperBound
                if row_range==0: rgb = 0
                else: rgb = 255 - int((itm.upperBound - row_min) / row_range * 255 ) 
                symbColor = (rgb<<16) + (rgb<<8) + rgb 
                label = itm.label
                width = 0.26
                # {'label': '1 - 1.4', 'lower': 1.0, 'symbColor': <PyQt5.QtGui.QColor ...BD9B9D4A0>, 'symbOpacity': 1.0, 'upper': 1.4}
                layerRenderer['properties']['ranges'].append({'lower':lower,'upper':upper,'symbColor':symbColor,'symbOpacity':1,'label':label,'width':width})

        else: return None
            
        return layerRenderer

    else: return None


def featureColorfromNativeRenderer(index: int, arcLayer: arcLayer) -> int:
    # case with one color for the entire layer
    #try:
    sym = arcLayer.symbology
    color = {'RGB': [100,100,100,100]}

    if sym.renderer.type == 'SimpleRenderer':
        print('SimpleRenderer')
        color = sym.renderer.symbol.color

    elif sym.renderer.type == 'UniqueValueRenderer':
        print('Unique Value Renderer')

        attribute = sym.renderer.fields[0]
        color = sym.renderer.defaultSymbol.color
        categories = sym.renderer.groups

        rows_attributes = arcpy.da.SearchCursor(arcLayer.dataSource, attribute)
        row_shapes_list = [x for k, x in enumerate(rows_attributes)]

        color_found = 0
        for i, grp in enumerate(categories):
            if color_found == 1: break
            for n, itm in enumerate(grp.items):
                for k, attrs in enumerate(row_shapes_list): 
                    if str(itm.values[0][0]) == "<Null>": itm.values[0][0] = None 
                    if k == index and ( str(attrs[0]) == str(itm.values[0][0]) or (attrs[0] is None and str(itm.values[0][0]) == "<Null>") ): 
                        color = itm.symbol.color
                        print("symbol color: ")
                        print(color)
                        color_found = 1
                        break 

    elif sym.renderer.type == 'GraduatedColorsRenderer' or sym.renderer.type == 'GraduatedSymbolsRenderer':
        print('Graduated Colors / Sybmols Renderer')
        attribute = sym.renderer.classificationField 
        rows_attributes = arcpy.da.SearchCursor(arcLayer.dataSource, attribute)
        row_shapes_list = [x for k, x in enumerate(rows_attributes)]

        rRanges = sym.renderer.classBreaks
        upperBounds = [-10000000000000000000]
        color_found = 0
        for itm in rRanges:
            print(itm)
            if color_found == 1: break
            for k, attrs in enumerate(row_shapes_list):  
                try:
                    if k == index and float(attrs[0]) <= float(itm.upperBound) and (k==0 or float(attrs[0]) > float(upperBounds[-1]) ):
                        color = itm.symbol.color
                        color_found = 1
                        break 
                except: pass
            upperBounds.append(itm.upperBound)

    elif sym.renderer.type == 'UnclassedColorsRenderer': 
        print('UnclassedColorsRenderer')
        attribute = sym.renderer.field  

        sym.updateRenderer('GraduatedColorsRenderer')
        sym.renderer.classificationField = attribute

        rows_attributes = arcpy.da.SearchCursor(arcLayer.dataSource, attribute)
        row_shapes_list = [x for k, x in enumerate(rows_attributes)]
        row_attrs = []
        row_max = -10000000000000000000
        row_min = 10000000000000000000
        feat_value = None
        for k, attrs in enumerate(row_shapes_list): 
            row_attrs.append(attrs[0])
            if attrs[0] < row_min: row_min = attrs[0]
            if attrs[0] > row_max: row_max = attrs[0]
            if k == index: feat_value = attrs[0]
        row_range = row_max - row_min
        breakCount = len(list(set(row_attrs))) # only unique values 
        sym.renderer.breakCount = breakCount

        # run as gradient colors 
        
        upperBounds = [-10000000000000000000]
        rRanges = sym.renderer.classBreaks

        for itm in rRanges:
            print(itm)
            try:
                if row_range!=0 and float(feat_value) <= float(itm.upperBound) and (len(upperBounds)==0 or float(feat_value) > float(upperBounds[-1])):
                    rgb = 255 - int((itm.upperBound - row_min) / row_range * 255 ) 
                    color = {'RGB':[rgb,rgb,rgb,100]}
                    print(color) 
                    break
            except: pass 
            upperBounds.append(itm.upperBound)

    else: 
        print('Else')
        return (100<<16) + (100<<8) + 100
    
    print("final color: ")
    print(color) 
    # construct RGB color
    col = symbol_color_to_speckle(color)
    print(col)
    return col


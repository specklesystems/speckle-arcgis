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
            if not os.path.exists(root_path + '\\Layers_Speckle\\rasters_Speckle'): os.makedirs(root_path + '\\Layers_Speckle\\rasters_Speckle')
            path_style = root_path + '\\Layers_Speckle\\rasters_Speckle\\' + newName + '_old.lyrx'
            path_style2 = root_path + '\\Layers_Speckle\\rasters_Speckle\\' + newName + '_new.lyrx'
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
                                    r,g,b = get_r_g_b(cl['color']) 
                                    itm.color = {'RGB': [r,g,b, 100]}
                                    itm.label = cl['label']
                                    itm.values = cl['value']
                        else: pass
                arcLayer.symbology = sym 
        else: 
            sym.updateColorizer('RasterStretchColorizer')
            arcLayer.symbology = sym
    return arcLayer
    

def rendererToSpeckle(project: ArcGISProject, active_map, arcLayer):
    print("_____rasterRenderer To Speckle______")
    if arcLayer.isRasterLayer: 
        try: 
            rType = arcLayer.symbology.colorizer.type # 'singleSymbol','categorizedSymbol','graduatedSymbol',
            if rType =='RasterStretchColorizer':  rType = 'singlebandgray'
            elif rType =='RasterUniqueValueColorizer':  rType = 'paletted' # only for 1-band raster 
            else: rType = 'singlebandgray'
        except: 
            rType = "multibandcolor"
            root_path = "\\".join(project.filePath.split("\\")[:-1])
            if not os.path.exists(root_path + '\\Layers_Speckle\\rasters_Speckle'): os.makedirs(root_path + '\\Layers_Speckle\\rasters_Speckle')
            path_style = root_path + '\\Layers_Speckle\\rasters_Speckle\\' + arcLayer.name + '_temp.lyrx'
            #path_style2 = root_path + '\\' + newName + '_new.lyrx'
            symJson = jsonFromLayerStyle(arcLayer, path_style)

        layerRenderer: dict[str, Any] = {}
        layerRenderer['type'] = rType
        print(rType)
        my_raster = arcpy.Raster(arcLayer.dataSource)  
        rasterBandNames = my_raster.bandNames

        if rType == "singlebandgray":  
            try: band = arcLayer.symbology.colorizer.band 
            except: band = 0 
            try: 
                bVals = my_raster.getRasterBands(rasterBandNames[band])
                bvalMin = bVals.minimum
                bvalMax = bVals.maximum
            except: 
                bvalMin = 0
                bvalMax = 0
            layerRenderer.update({'properties': {'max':0,'min':0,'band':band+1,'contrast':0}}) 

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
                rbVals = my_raster.getRasterBands(rasterBandNames[redBand-1])
                rbvalMin = rbVals.minimum
                rbvalMax = rbVals.maximum
            except: 
                rbvalMin = 0
                rbvalMax = 0
            try: 
                gbVals = my_raster.getRasterBands(rasterBandNames[greenBand-1])
                gbvalMin = gbVals.minimum
                gbvalMax = gbVals.maximum
            except: 
                gbvalMin = 0
                gbvalMax = 0
            try: 
                bbVals = my_raster.getRasterBands(rasterBandNames[blueBand-1])
                bbvalMin = bbVals.minimum
                bbvalMax = bbVals.maximum
            except: 
                bbvalMin = 0
                bbvalMax = 0

            layerRenderer.update({'properties': {'greenBand':greenBand,'blueBand':blueBand,'redBand':redBand}})
            layerRenderer['properties'].update({'redContrast':0,'redMin':0,'redMax':0})
            layerRenderer['properties'].update({'greenContrast':0,'greenMin':0,'greenMax':0})
            layerRenderer['properties'].update({'blueContrast':0,'blueMin':0,'blueMax':0})
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


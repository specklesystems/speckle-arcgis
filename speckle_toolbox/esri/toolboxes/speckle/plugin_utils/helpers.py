import os
from typing import List
import inspect 

def findOrCreatePath(path: str):
    if not os.path.exists(path): 
        os.makedirs(path)

def removeSpecialCharacters(text: str) -> str:
    new_text = text.replace("[","_").replace("]","_").replace(" ","_").replace("-","_").replace("(","_").replace(")","_").replace(":","_").replace("\\","_").replace("/","_").replace("\"","_").replace("&","_").replace("@","_").replace("$","_").replace("%","_").replace("^","_")
    #new_text = text.encode('iso-8859-1', errors='ignore').decode('utf-8')
    return new_text

def splitTextIntoLines(text: str = "", number: int= 40) -> str: 
    print("__splitTextIntoLines")
    print(text)
    msg = ""
    try:
        if len(text)>number:
            try:
                for i, x in enumerate(text):
                    msg += x
                    if i!=0 and i%number == 0: msg += "\n"
            except Exception as e: print(e)
        else: 
            msg = text
    except Exception as e:
        print(e)
        print(text)
    
    return msg

def validateNewFclassName(newName: str, prefix: str, all_layer_names: List[str]) -> str:
    
    fixed_name = newName

    if (prefix + fixed_name) in all_layer_names: 
    
        layerNameCreated = 0
        for index, letter in enumerate('234567890abcdefghijklmnopqrstuvwxyz'):
            if ((prefix + fixed_name) + "_" + letter) not in all_layer_names: 
                fixed_name += "_"+letter
                layerNameCreated +=1
                break 
        if layerNameCreated == 0:
            for index, letter in enumerate('234567890abcdefghijklmnopqrstuvwxyz'):
                test_fixed_name = validateNewFclassName((fixed_name + "_" + letter), prefix, all_layer_names)
                if (prefix + test_fixed_name) not in all_layer_names: 
                    fixed_name = test_fixed_name 
                    layerNameCreated +=1
                    break 
                #else: layerNameCreated +=1

        if layerNameCreated == 0:
            pass #logToUser('Feature class name already exists', level=2, func = inspect.stack()[0][3])
            #return fixed_name

    return fixed_name
    
def findFeatColors(fetColors, f):
    
    colorFound = 0
    try: # get render material from any part of the mesh (list of items in displayValue)
        for k, item in enumerate(f.displayValue):
            try:
                fetColors.append(item.renderMaterial.diffuse)  
                colorFound += 1
                break
            except: pass
        if colorFound == 0: fetColors.append(f.renderMaterial.diffuse)
    except: 
        try:
            for k, item in enumerate(f["@displayValue"]):
                try: 
                    fetColors.append(item.renderMaterial.diffuse) 
                    colorFound += 1
                    break
                except: pass
            if colorFound == 0: fetColors.append(f.renderMaterial.diffuse)
        except: 
            # the Mesh itself has a renderer 
            try: # get render material from any part of the mesh (list of items in displayValue)
                fetColors.append(f.renderMaterial.diffuse)  
                colorFound += 1
            except: 
                try:
                    fetColors.append(f.displayStyle.color) 
                    colorFound += 1
                except: pass
    if colorFound == 0: fetColors.append(None)
    return fetColors

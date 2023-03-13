import os
from typing import List
import inspect 

try:
    from speckle.plugin_utils.logger import logToUser
except:
    from speckle_toolbox.esri.toolboxes.speckle.plugin_utils.logger import logToUser


def findOrCreatePath(path: str):
    if not os.path.exists(path): 
        os.makedirs(path)

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
            logToUser('Feature class name already exists', level=2, func = inspect.stack()[0][3])
            #return fixed_name

    return fixed_name
    
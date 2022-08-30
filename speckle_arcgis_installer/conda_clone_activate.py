# clone env, install toolbox & dependencies into the cloned env; and into current one (if not default) 
import sys
import sysconfig
import os.path
from os.path import isfile, join
from os import listdir
import subprocess
from subprocess import CalledProcessError
from subprocess_call import subprocess_call

from msilib.schema import Error
import sys

import arcpy 

def setup():
    #print(plugin_dir) 
    pythonExec = get_python_path() # import numpy; import os; print(os.path.abspath(numpy.__file__)) 
    #print(pythonExec)
    
    if pythonExec is None: # env is default, need to restart ArcGIS
        return False
    
def get_python_path(): # create a full copy of default env 
    # or: import site; site.getsitepackages()[0]
    # import specklepy; import os; print(os.path.abspath(specklepy.__file__)) ##currentPythonExec = sysconfig.get_paths()['data'] + r"\python.exe"

    pythonExec = os.environ["ProgramFiles"] + r'\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe' #(r"%PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe") #os.path.dirname(sys.executable) + "\\python.exe" # default python.exe
    #print(pythonExec)
    if sys.platform == "win32":
        env_new_name = "arcgispro-py3-speckle"
        #clone_env(pythonExec, env_new_name) # only if doesn't exist yet 
        activate_env(env_new_name)
        return pythonExec
    else: pass

def clone_env(pythonExec_old: str, env_new_name: str): 
    install_folder = os.getenv('APPDATA').replace("\\Roaming","") + r"\Local\ESRI\conda\envs"   #r"%LOCALAPPDATA%\ESRI\conda\envs" 
    #print("Clone default ArcGIS Pro conda env")
    #print(install_folder)
    #if not os.path.exists(install_folder): os.makedirs(install_folder)
    
    default_env = pythonExec_old.replace("Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe","Pro\\bin\\Python\\envs\\arcgispro-py3") # + "\\" + 'arcgispro-py3'
    conda_exe = pythonExec_old.replace("Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe","Pro\\bin\\Python\\Scripts\\conda.exe") #%PROGRAMFILES%\ArcGIS\Pro\bin\Python\Scripts\conda.exe #base: %PROGRAMDATA%\Anaconda3\condabin\conda.bat
    new_env = install_folder + "\\" + env_new_name # %LOCALAPPDATA%\ESRI\conda\envs\...

    subprocess_call( [ conda_exe, 'create', '--clone', default_env, '-p', new_env] ) # will not execute if already exists

    return new_env + "\\python.exe"

def activate_env(env_new_name: str):
    # using Popen, because process does not return result; subprocess.run will hang indefinitely 
    variable = subprocess.Popen((f'proswap {env_new_name}'),stdout = subprocess.PIPE,stderr = subprocess.PIPE,text = True,shell = True)
    #print(variable) 
    # activate new env : https://support.esri.com/en/technical-article/000024206

setup()

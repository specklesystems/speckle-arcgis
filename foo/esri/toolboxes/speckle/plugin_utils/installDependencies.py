import sys
import sysconfig
import os.path
from os.path import isfile, join
from os import listdir

from msilib.schema import Error
import sys

from speckle.plugin_utils.subprocess_call import subprocess_call
import arcpy 

# only activation of speckle env (if default) / or installation of packages into current dev

def setup():
    #print(plugin_dir) 
    pythonExec = get_python_path() # import numpy; import os; print(os.path.abspath(numpy.__file__)) 
    print(pythonExec)
    
    if pythonExec is None: # env is default, need to restart ArcGIS
        return False
    
def get_python_path():
    #pythonExec = os.path.dirname(sys.executable) # e.g. 'C:\\Program Files\\ArcGIS\\Pro\\bin': doesn't reflect which env is used.  C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3 
    pythonExec = sysconfig.get_paths()['data'] + r"\python.exe" # e.g. %PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3 or C:\Users\Kateryna\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone  # or: import site; site.getsitepackages()[0]
    if sys.platform == "win32":
        env_new_name = "arcgispro-py3-speckle2"

        if pythonExec.endswith(r"\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"): 
            subprocess_call(['proswap', env_new_name]) # activate new env : https://support.esri.com/en/technical-article/000024206
            return None # show message, need to restart 

        else: #install to current env
            installToolbox(pythonExec)
            installDependencies(pythonExec)

        return pythonExec
    else: pass

def installToolbox(newExec: str):
    subprocess_call([newExec, '-m','pip', 'install', 'C:\\Users\\Kateryna\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\dist\\foo-0.1-py3-none-any.whl'])
    # to uninstall: cmd.exe "C:\\Users\\Kateryna\\AppData\\Local\\ESRI\\conda\\envs\\arcgispro-py3-speckle\\python.exe" -m pip uninstall C:\\Users\\Kateryna\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\dist\\foo-0.1-py3-none-any.whl
    return

def installDependencies(pythonExec: str):
    print(os.path.join(os.path.dirname(__file__), "get_pip.py"))
    try:
        import pip
    except:
        #arcpy.AddMessage("Pip not installed, setting up now")
        getPipFilePath = os.path.join(os.path.dirname(__file__), "get_pip.py") #TODO: give actual folder path 
        exec(open(getPipFilePath).read())

        # just in case the included version is old
        subprocess_call([pythonExec, "-m", "pip", "install", "--upgrade", "pip"])
    
    pkgVersion = "2.7.4" 
    pkgName = "specklepy"
    try:
        import specklepy # wrong installation: C:\Users\Kateryna\AppData\Roaming\Python\Python37\site-packages\specklepy\__init__.py 
    except Exception as e:
        #arcpy.AddMessage("Specklepy not installed")
        #print("Specklepy not installed")
        subprocess_call([ pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"])

    
    pkgVersion = "1.10.11" 
    pkgName = "panda3d"
    try:
        import panda3d
    except Exception as e:
        print("panda3d not installed")
        subprocess_call( [pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"])

    # Check if specklpy needs updating
    try:
        arcpy.AddMessage(f"Attempting to update specklepy to {pkgVersion}")
        print(f"Attempting to update specklepy to {pkgVersion}")
        print(pythonExec )
        # pip.main(['install', "specklepy==2.7.4"])
        result = subprocess_call(
            [
                pythonExec,
                "-m",
                "pip",
                "install",
                "--upgrade",
                f"{pkgName}=={pkgVersion}",
            ]
        )
        if result == True:
            print("specklepy upgraded")
            return True
        else: 
            return False

    except Exception as e:
        print(e)
        print(e.with_traceback)
        arcpy.AddMessage(e.with_traceback)
    return True


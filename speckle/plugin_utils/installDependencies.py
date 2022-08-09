import sys
import sysconfig
import os.path
from os.path import isfile, join
from os import listdir
import subprocess

from speckle.plugin_utils.subprocess_call import subprocess_call
import arcpy 

def get_qgis_python_path():
    #pythonExec = os.path.dirname(sys.executable)# C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3 
    # ?? cloned venv is ignored, even if set up as default
    pythonExec = "\"" + sysconfig.get_paths()['data'] + "\python.exe" + "\"" # or: import site; site.getsitepackages()[0]
    #if sys.platform == "win32":
        #folder = [f for f in listdir(pythonExec + "\\Python\\envs")][0] # by default "arcgispro-py3"
        #pythonExec +=  "\\Python\\envs\\" + folder
    #else:
    #    return None

    print(pythonExec) 
    if pythonExec.endswith(r"\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"): return
    ## should be: C:\Users\[UserName]\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone
    # or default: C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3
    # in other form: %PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3
    ## try: https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/installing-python-for-arcgis-pro.htm#ESRI_SECTION2_7FDA7FD13D724C51B442D8859F3A25A8
    # %PROGRAMFILES%\ArcGIS\Pro\bin\Python\Scripts\ OR %LOCALAPPDATA%\ArcGIS\Pro\bin\Python\Scripts\
    return pythonExec

def clone_env(pythonExec: str): 
    # EVERYTHING HERE: https://developers.arcgis.com/python/guide/understanding-conda/
    #then https://support.esri.com/en/technical-article/000024206
    
    # https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#cloning-an-environment
    arcpy.AddMessage("Clone env")
    print("Clone env")
    winExec = r"%SystemRoot%\System32\cmd.exe"
    defaultEnvFolder = pythonExec.replace(str(r"\python.exe"),"")
    install_folder = r"%LOCALAPPDATA%\ESRI\conda\envs"
    env_new_name = "arcgispro-py3-speckle-clone"
    #create specs file conda list --explicit > spec-file.txt
    #commands = f"conda list --explicit > {install_folder}\spec-file.txt" #cd {defaultEnvFolder}; 
    
    #subprocess_call([f"{winExec}", "conda", "list", "--explicit", ">", f"{install_folder}\spec-file.txt"])
    return 
    
    #subprocess_call([pythonExec, "conda", "install", "--name", f{env_new_name}, "--file", f"{install_folder}\spec-file.txt"])
    #subprocess_call([install_folder, "conda", "activate", f"{env_new_name}"]) 
    #return install_folder + "\" + env_new_name

def setup():
    plugin_dir = os.path.dirname(__file__) 
    print(plugin_dir) 
    pythonExec = get_qgis_python_path() 
    print(pythonExec)

    if str(r"ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe") in pythonExec: 
        pythonExec = clone_env(pythonExec) 
        return False
    #return 

    try:
        import pip
    except:
        arcpy.AddMessage("Pip not installed, setting up now")
        getPipFilePath = os.path.join(plugin_dir, "plugin_utils/get_pip.py")
        exec(open(getPipFilePath).read())

        # just in case the included version is old
        subprocess_call([pythonExec, "-m", "pip", "install", "--upgrade", "pip"])
    
    pkgVersion = "2.7.4" 
    pkgName = "specklepy"
    try:
        import specklepy # import specklepy; import os; print(os.path.abspath(specklepy.__file__)) 
        # C:\Users\Kateryna\AppData\Roaming\Python\Python37\site-packages\specklepy\__init__.py 
    except Exception as e:
        arcpy.AddMessage("Specklepy not installed")
        print("Specklepy not installed")
        subprocess_call([pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"])

    # Check if specklpy needs updating
    try:
        arcpy.AddMessage(f"Attempting to update specklepy to {pkgVersion}")
        print(f"Attempting to update specklepy to {pkgVersion}")
        # pip.main(['install', "specklepy==2.7.4"])
        subprocess_call(
            [
                pythonExec,
                "-m",
                "pip",
                "install",
                "--upgrade",
                f"{pkgName}=={pkgVersion}",
            ]
        )
        print("specklepy upgraded")

    except Exception as e:
        print(e)
        print(e.with_traceback)
        arcpy.AddMessage(e.with_traceback)
    return True

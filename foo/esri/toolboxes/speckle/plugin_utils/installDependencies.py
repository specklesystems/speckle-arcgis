import sys
import sysconfig
import os.path
from os.path import isfile, join
from os import listdir
import subprocess

from speckle.plugin_utils.subprocess_call import subprocess_call
import arcpy 

def get_python_path():
    #pythonExec = os.path.dirname(sys.executable) # e.g. 'C:\\Program Files\\ArcGIS\\Pro\\bin': doesn't reflect which env is used.  C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3 
    pythonExec = sysconfig.get_paths()['data'] + r"\python" # e.g. %PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3 or C:\Users\Kateryna\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone  # or: import site; site.getsitepackages()[0]
    if sys.platform == "win32":
        env_new_name = "arcgispro-py3-speckle"
        clone_env(pythonExec, env_new_name) # only if doesn't exist yet 

        if pythonExec.endswith(r"\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python"): 
            subprocess_call(['proswap', env_new_name]) # activate new env : https://support.esri.com/en/technical-article/000024206
            return None # show message, need to restart 
        return pythonExec
    else: pass

def clone_env(pythonExec_old: str, env_new_name: str): # ONLY works if ArcGIS is opened as Admin 

    install_folder = r"%LOCALAPPDATA%\ESRI\conda\envs" 
    #if not os.path.exists(install_folder): os.makedirs(install_folder)
    
    default_env = pythonExec_old.replace("py3\\python","py3") # + "\\" + 'arcgispro-py3'
    conda_exe = default_env.replace("envs\\arcgispro-py3","Scripts\\conda.exe") #%PROGRAMFILES%\ArcGIS\Pro\bin\Python\Scripts\conda.exe #base: %PROGRAMDATA%\Anaconda3\condabin\conda.bat
    new_env = install_folder + "\\" + env_new_name # %LOCALAPPDATA%\ESRI\conda\envs\...

    if not os.path.exists(new_env):         
        subprocess_call( [conda_exe, 'create', '--clone', default_env, '-p', new_env] )
        # another way: 
        # spec_file = install_folder + "\\def_env_spec.txt" 
        # subprocess_call( [conda_exe, 'list', '--explicit', '>', spec_file] )
        # subprocess_call( [conda_exe, 'create', '--prefix', new_env, '--file', spec_file] )
    return 

def setup():
    plugin_dir = os.path.dirname(__file__) 
    #print(plugin_dir) 
    pythonExec = get_python_path() # import numpy; import os; print(os.path.abspath(numpy.__file__)) 
    print(pythonExec)

    if pythonExec is None: # env is default, need to restart ArcGIS
        return False
    ##################### install dependencies ###################################
    
    try:
        import pip
    except:
        #arcpy.AddMessage("Pip not installed, setting up now")
        getPipFilePath = os.path.join(plugin_dir, "plugin_utils/get_pip.py")
        exec(open(getPipFilePath).read())

        # just in case the included version is old
        subprocess_call([pythonExec, "-m", "pip", "install", "--upgrade", "pip"])
    
    pkgVersion = "2.7.4" 
    pkgName = "specklepy"
    try:
        import specklepy 
        # C:\Users\Kateryna\AppData\Roaming\Python\Python37\site-packages\specklepy\__init__.py 
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
    
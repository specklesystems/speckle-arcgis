# import sysconfig; import subprocess; x = sysconfig.get_paths()['data'] + r"\python.exe"; subprocess.run((x, 'C:\\Users\\Kateryna\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\speckleArcgisInstall.py'), capture_output=True, text=True, shell=True, timeout=1000 )

import sys
import sysconfig
import os.path
from os.path import isfile, join
from os import listdir
import subprocess
from subprocess import CalledProcessError

from msilib.schema import Error
import sys

import arcpy 

# clone env, install toolbox & dependencies into the cloned env; and into current one (if not default) 

def setup():
    #print(plugin_dir) 
    pythonExec = get_python_path() # import numpy; import os; print(os.path.abspath(numpy.__file__)) 
    print(pythonExec)
    
    if pythonExec is None: # env is default, need to restart ArcGIS
        return False
    
def get_python_path(): # create a full copy of default env 
    pythonExec = os.path.join("%PROGRAMFILES%", "\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe") #sysconfig.get_paths()['data'] + r"\python" # e.g. %PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3 or C:\Users\Kateryna\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone  # or: import site; site.getsitepackages()[0]
    print(pythonExec)
    #pythonExec = os.path.dirname(sys.executable) + "\\Python\\envs\\arcgispro-py3\\python.exe" # default python.exe
    if sys.platform == "win32":
        env_new_name = "arcgispro-py3-speckle2"
        #p = '\"' + pythonExec + '\"'
        newExec = clone_env(pythonExec, env_new_name) # only if doesn't exist yet 

        # install toolbox to cloned (spare) env
        installToolbox(newExec)
        installDependencies(newExec)

        currentPythonExec = sysconfig.get_paths()['data'] + r"\python.exe"
        print(currentPythonExec)
        if currentPythonExec.endswith(r"\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"): 
            subprocess_call(['proswap', env_new_name]) # activate new env : https://support.esri.com/en/technical-article/000024206
            return None # show message, need to restart 
        else: 
            installToolbox(currentPythonExec)
            installDependencies(currentPythonExec)

        return pythonExec
    else: pass

def clone_env(pythonExec_old: str, env_new_name: str): # ONLY works if ArcGIS is opened as Admin 
    install_folder = r"%LOCALAPPDATA%\ESRI\conda\envs" 
    #if not os.path.exists(install_folder): os.makedirs(install_folder)
    
    default_env = pythonExec_old.replace("py3\\python.exe","py3") # + "\\" + 'arcgispro-py3'
    conda_exe = pythonExec_old.replace("envs\\arcgispro-py3\\python.exe","Scripts\\conda.exe") #%PROGRAMFILES%\ArcGIS\Pro\bin\Python\Scripts\conda.exe #base: %PROGRAMDATA%\Anaconda3\condabin\conda.bat
    new_env = install_folder + "\\" + env_new_name # %LOCALAPPDATA%\ESRI\conda\envs\...

    #if not os.path.exists(new_env):  
    c = r'"' + conda_exe + r'"'
    d = r'"' + default_env + r'"'
    n = r'"' + new_env + r'"'
    subprocess_call( [ c, 'create', '--clone', d, '-p', n] ) # will not execute if already exists

    return new_env + "\\python.exe"

def installToolbox(newExec: str):
    whl_file = os.path.join(os.path.dirname(__file__), "foo-0.1-py3-none-any.whl" ) # 'C:\\Users\\Kateryna\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\dist\\foo-0.1-py3-none-any.whl'
    subprocess_call([newExec, '-m','pip', 'install', whl_file])
    # to uninstall: cmd.exe "C:\\Users\\Kateryna\\AppData\\Local\\ESRI\\conda\\envs\\arcgispro-py3-speckle\\python.exe" -m pip uninstall C:\\Users\\Kateryna\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\dist\\foo-0.1-py3-none-any.whl
    return

def installDependencies(pythonExec: str):
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


IS_WIN32 = 'win32' in str(sys.platform).lower()

def subprocess_call(*args, **kwargs):
    #also works for Popen. It creates a new *hidden* window, so it will work in frozen apps (.exe).
    if IS_WIN32:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags = subprocess.CREATE_NEW_CONSOLE | subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = startupinfo
        print("start")
    try: 
        # if manually: cmd.exe -> conda activate [env folder] -> pip install specklepy 
        result = subprocess.run(*args, capture_output=True, shell=True, timeout=1000)
        print(result)
        #result = subprocess.Popen( arg, shell=True, stdout=subprocess.PIPE) #, stderr=subprocess.STDOUT)
        #retcode = subprocess.check_call(*args, **kwargs) # Creates infinite loop, known issue: https://github.com/python/cpython/issues/87512
    except CalledProcessError as e: 
        print("ERROR: " + e.output)
        return False
    except subprocess.TimeoutExpired as e: 
        print("Timeout Error: " + str(e.args[0])) # e.g. Defaulting to user installation because normal site-packages is not writeable
        return False
    except Exception as e: 
        print(str(e))
        return False
    except: print("unknown error") 
    print("end")
    return True


setup()

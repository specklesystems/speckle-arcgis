# clone env, install toolbox & dependencies into the cloned env; and into current one (if not default) 
import sys
import sysconfig
import os.path
from os.path import isfile, join
from os import listdir
import subprocess
from subprocess import CalledProcessError
from subprocess_call import subprocess_call

import sys

def setup():
    pythonExec = get_python_path() # import numpy; import os; print(os.path.abspath(numpy.__file__)) 
    return pythonExec # None if not successful 
    
def get_python_path(): # create a full copy of default env 
    #print("Get Python path")
    # or: import site; site.getsitepackages()[0]
    # import specklepy; import os; print(os.path.abspath(specklepy.__file__)) ##currentPythonExec = sysconfig.get_paths()['data'] + r"\python.exe"

    pythonExec = os.environ["ProgramFiles"] + r'\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe' #(r"%PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe") #os.path.dirname(sys.executable) + "\\python.exe" # default python.exe
    #print(pythonExec)
    if not os.path.exists(pythonExec):
        pythonExec = os.getenv('APPDATA') + r'\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe'
        if not os.path.exists(pythonExec): return None
    #print(os.getenv('APPDATA') + r'\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe')

    if sys.platform == "win32":
        env_new_name = "arcgispro-py3-speckle"
        newExec = clone_env(pythonExec, env_new_name) # only if doesn't exist yet 
        if not os.path.exists(newExec): return None
        
        activate_env(env_new_name)
        return newExec
    else: return None

def clone_env(pythonExec_old: str, env_new_name: str): 
    install_folder = os.getenv('APPDATA').replace("\\Roaming","") + r"\Local\ESRI\conda\envs"   #r"%LOCALAPPDATA%\ESRI\conda\envs" 
    if not os.path.exists(install_folder): os.makedirs(install_folder)
    
    default_env = pythonExec_old.replace("Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe","Pro\\bin\\Python\\envs\\arcgispro-py3") # + "\\" + 'arcgispro-py3'
    conda_exe = pythonExec_old.replace("Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe","Pro\\bin\\Python\\Scripts\\conda.exe") #%PROGRAMFILES%\ArcGIS\Pro\bin\Python\Scripts\conda.exe #base: %PROGRAMDATA%\Anaconda3\condabin\conda.bat
    new_env = install_folder + "\\" + env_new_name # %LOCALAPPDATA%\ESRI\conda\envs\...

    subprocess_call( [ conda_exe, 'config', '--set', 'ssl_verify', 'False'] )
    print("Press Enter to continue")
    #print(conda_exe)
    #print(default_env)
    #print(new_env)
    subprocess_call( [ conda_exe, 'create', '--clone', default_env, '-p', new_env] ) # will not execute if already exists
    subprocess_call( [ conda_exe, 'config', '--set', 'ssl_verify', 'True'] )
    
    print(new_env + "\\python.exe")
    return new_env + "\\python.exe"

def activate_env(env_new_name: str):
    # using Popen, because process does not return result; subprocess.run will hang indefinitely 
    variable = subprocess.Popen((f'proswap {env_new_name}'),stdout = subprocess.PIPE,stderr = subprocess.PIPE,text = True,shell = True)
    # activate new env : https://support.esri.com/en/technical-article/000024206


def installToolbox(newExec: str):
    print("Installing Speckle Toolbox")
    whl_file = os.path.join(os.path.dirname(__file__), "speckle_toolbox-2.9.4-py3-none-any.whl" ) 
    print(whl_file)
    subprocess_call([newExec, '-m','pip','install','--upgrade', '--force-reinstall', whl_file])
    # to uninstall: cmd.exe "C:\\Users\\username\\AppData\\Local\\ESRI\\conda\\envs\\arcgispro-2.9.4-py3-none-any.whl
    return

def installDependencies(pythonExec: str, pkgName: str, pkgVersion: str):
    # install pip
    print(pythonExec)
    try:
        import pip
    except:
        getPipFilePath = os.path.join(os.path.dirname(__file__), "get_pip.py") #TODO: give actual folder path 
        exec(open(getPipFilePath).read())
        # just in case the included version is old
        subprocess_call([pythonExec, "-m", "pip", "install", "--upgrade", "pip"])
        
    # install package
    try:
        import importlib
        importlib.import_module(pkgName)
    except Exception as e:
        print(f"{pkgName} not installed")
        subprocess_call( [pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"])

    # Check if package needs updating
    try:
        print(f"Attempting to update {pkgName} to {pkgVersion}")
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
            print(f"{pkgName} upgraded")
            return True
        else: 
            return False
    except Exception as e:
        print(e)
        print(e.with_traceback)
    return True
    
pythonPath = setup()
if pythonPath is not None:
    installToolbox(pythonPath)
    installDependencies(pythonPath, "specklepy", "2.9.0"  )
    installDependencies(pythonPath, "panda3d", "1.10.11" )

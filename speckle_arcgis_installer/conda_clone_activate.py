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

ENV_NEW_NAME = "arcgispro-py3-speckle"

def setup():
    pythonExec = get_python_path() # import numpy; import os; print(os.path.abspath(numpy.__file__)) 
    return pythonExec # None if not successful 
    
def get_default_python():
    pythonExec = os.environ["ProgramFiles"] + r'\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe' #(r"%PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe") #os.path.dirname(sys.executable) + "\\python.exe" # default python.exe
    #print(pythonExec)
    if not os.path.exists(pythonExec):
        pythonExec = os.getenv('APPDATA').replace("Roaming", "Local") + r'\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe'
        if not os.path.exists(pythonExec): return None
    return pythonExec

def get_python_path(): # create a full copy of default env 
    #print("Get Python path")
    # or: import site; site.getsitepackages()[0]
    # import specklepy; import os; print(os.path.abspath(specklepy.__file__)) ##currentPythonExec = sysconfig.get_paths()['data'] + r"\python.exe"
    def_exec = get_default_python()
    #print(os.getenv('APPDATA') + r'\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe')

    if sys.platform == "win32":
        newExec = clone_env(def_exec) # only if doesn't exist yet 
        if not os.path.exists(newExec): return None
        
        activate_env()
        return newExec
    else: return None

def clone_env(pythonExec_old: str): 
    install_folder = os.getenv('APPDATA').replace("\\Roaming","") + r"\Local\ESRI\conda\envs"   #r"%LOCALAPPDATA%\ESRI\conda\envs" 
    if not os.path.exists(install_folder): os.makedirs(install_folder)
    
    default_env = pythonExec_old.replace("Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe","Pro\\bin\\Python\\envs\\arcgispro-py3") # + "\\" + 'arcgispro-py3'
    conda_exe = pythonExec_old.replace("Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe","Pro\\bin\\Python\\Scripts\\conda.exe") #%PROGRAMFILES%\ArcGIS\Pro\bin\Python\Scripts\conda.exe #base: %PROGRAMDATA%\Anaconda3\condabin\conda.bat
    new_env = install_folder + "\\" + ENV_NEW_NAME # %LOCALAPPDATA%\ESRI\conda\envs\...

    if os.path.exists(conda_exe) and os.path.exists(default_env) and os.path.exists(new_env) and not os.path.exists(new_env + "\\python.exe"): 
        # conda environment invalid: delete it's folder 
        print(f"Removing invalid environment {new_env}")
        os.remove(new_env)

    if os.path.exists(conda_exe) and os.path.exists(default_env) and not os.path.exists(new_env): 
        print("Wait for the default ArcGIS Pro conda environment to be cloned")
        subprocess_call( [ conda_exe, 'config', '--set', 'ssl_verify', 'False'] )
        subprocess_call( [ conda_exe, 'create', '--clone', default_env, '-p', new_env] ) # will not execute if already exists
        subprocess_call( [ conda_exe, 'config', '--set', 'ssl_verify', 'True'] )

    elif os.path.exists(new_env) and os.path.exists(new_env + "\\python.exe"):
        print(f"Environment {new_env} already exists, preparing to install packages..")

    print(new_env + "\\python.exe")
    return new_env + "\\python.exe"

def activate_env():
    # using Popen, because process does not return result; subprocess.run will hang indefinitely 
    variable = subprocess.Popen((f'proswap {ENV_NEW_NAME}'),stdout = subprocess.PIPE,stderr = subprocess.PIPE,text = True,shell = True)
    # activate new env : https://support.esri.com/en/technical-article/000024206


def installToolbox(newExec: str):
    print("Installing Speckle Toolbox")
    whl_file = os.path.join(os.path.dirname(__file__), "speckle_toolbox-2.9.4-py3-none-any.whl" ) 
    print(whl_file)
    subprocess_call([newExec, '-m','pip','install','--upgrade', '--force-reinstall', whl_file])
    # to uninstall: cmd.exe "X:\\xxx.whl
    return

def clearToolbox(pythonExec: str):
    # install pip
    print("CLEAR toolbox")
    print(pythonExec)
    try:
        
        speckle_path = pythonExec.replace("python.exe","Lib\\site-packages\\") 
        
        print(speckle_path)
        paths = os.listdir(speckle_path)
        for p in paths:
            if "speckle_toolbox" in p:
                print("remove: " + str(p))
                os.remove(p)
    except Exception as e:
        print(e)
        pass

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
        #import importlib #importlib.import_module(pkgName)
        if pkgName == "specklepy":
            import specklepy 
            if pythonExec.replace("\\python.exe","") not in (os.path.abspath(specklepy.__file__)): 
                print(f"Installing {pkgName} to {pythonExec}")
                #subprocess_call( [pythonExec, "-m", "pip", "uninstall", f"{pkgName}"])
                subprocess_call( [pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"])
        elif pkgName == "panda3d":
            import panda3d 
            if pythonExec.replace("\\python.exe","") not in (os.path.abspath(panda3d.__file__)): 
                print(f"Installing {pkgName} to {pythonExec}")
                subprocess_call( [pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"])
        elif pkgName == "PyQt5":
            import PyQt5 
            if pythonExec.replace("\\python.exe","") not in (os.path.abspath(PyQt5.__file__)): 
                print(f"Installing {pkgName} to {pythonExec}")
                subprocess_call( [pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"])
    except Exception as e:
        print(f"{pkgName} not installed")
        subprocess_call( [pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"])

    # Check if package needs updating
    r'''
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
    '''
    return True
    
pythonPath = setup()
print(pythonPath)
if pythonPath is not None:

    #def_exec = get_default_python()
    #conda_exe = def_exec.replace("Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe","Pro\\bin\\Python\\Scripts\\conda.exe") #%PROGRAMFILES%\ArcGIS\Pro\bin\Python\Scripts\conda.exe #base: %PROGRAMDATA%\Anaconda3\condabin\conda.bat
    #subprocess_call([conda_exe, 'proup','-n', ENV_NEW_NAME])
    
    clearToolbox(pythonPath)
    installToolbox(pythonPath)
    installDependencies(pythonPath, "specklepy", "2.17.12"  )
    installDependencies(pythonPath, "panda3d", "1.10.11" )
    installDependencies(pythonPath, "PyQt5", "5.15.9" )

# manual: import sysconfig; import subprocess; x = sysconfig.get_paths()['data'] + r"\python.exe"; subprocess.run((x, "-m", "pip", "install", "PyQt5==5.15.9"), capture_output=True, text=True, shell=True, timeout=1000 )

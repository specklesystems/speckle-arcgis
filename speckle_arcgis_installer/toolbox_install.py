
from subprocess_call import subprocess_call
import os 

pythonPath = os.getenv('APPDATA').replace("\\Roaming","") + r"\Local\ESRI\conda\envs\arcgispro-py3-speckle\python.exe"

def installToolbox(newExec: str):
    print("Installing Speckle Toolbox")
    whl_file = os.path.join(os.path.dirname(__file__), "speckle_toolbox-2.30.0-py3-none-any.whl" ) 
    print(whl_file)
    subprocess_call([newExec, '-m','pip','install','--upgrade', '--force-reinstall', whl_file])
    # to uninstall: cmd.exe "C:\\Users\\username\\AppData\\Local\\ESRI\\conda\\envs\\arcgispro-2.30.0-py3-none-any.whl
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
        print(f"Attempting to update panda3d to {pkgVersion}")
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


installToolbox(pythonPath)
installDependencies(pythonPath, "specklepy", "2.9.0"  )
installDependencies(pythonPath, "panda3d", "1.10.11" )


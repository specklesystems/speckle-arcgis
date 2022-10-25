
from subprocess_call import subprocess_call
import os 

pythonPath = os.getenv('APPDATA').replace("\\Roaming","") + r"\Local\ESRI\conda\envs\arcgispro-py3-speckle\python.exe"

def installToolbox(newExec: str):
    print("Installing Speckle Toolbox")
    whl_file = os.path.join(os.path.dirname(__file__), "speckle_toolbox-2.9.3-py3-none-any.whl" ) 
    print(whl_file)
    subprocess_call([newExec, '-m','pip','install','--upgrade', '--force-reinstall', whl_file])
    # to uninstall: cmd.exe "C:\\Users\\username\\AppData\\Local\\ESRI\\conda\\envs\\arcgispro-2.9.3-py3-none-any.whl
    return

def installDependencies(pythonExec: str):
    #print("Installing dependencies")
    print(pythonExec)
    try:
        import pip
    except:
        getPipFilePath = os.path.join(os.path.dirname(__file__), "get_pip.py") #TODO: give actual folder path 
        exec(open(getPipFilePath).read())

        # just in case the included version is old
        subprocess_call([pythonExec, "-m", "pip", "install", "--upgrade", "pip"])
    
    pkgVersion = "2.9.0" 
    pkgName = "specklepy"
    try:
        import specklepy # C:\Users\username\AppData\Roaming\Python\Python37\site-packages\specklepy\__init__.py 
    except Exception as e:
        subprocess_call([ pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"])

    # Check if specklpy needs updating
    try:
        print(f"Attempting to update specklepy to {pkgVersion}")
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

    pkgVersion = "1.10.11" 
    pkgName = "panda3d"
    try:
        import panda3d
    except Exception as e:
        print("panda3d not installed")
        subprocess_call( [pythonExec, "-m", "pip", "install", f"{pkgName}=={pkgVersion}"])

    # Check if specklpy needs updating
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
            print("dependencies upgraded")
            return True
        else: 
            return False

    except Exception as e:
        print(e)
        print(e.with_traceback)
    return True

installToolbox(pythonPath)
installDependencies(pythonPath)


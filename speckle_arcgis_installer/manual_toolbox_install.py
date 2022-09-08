# MANUAL INSTALLATION: 
#   1. enter correct path to Python exe of your new environemnt in line 10 
#   2. enter the location of 'manual_toolbox_install.py' in the following command and run this command in ArcGIS Python console (View -> Python Window)
#   import sysconfig; import subprocess; x = sysconfig.get_paths()['data'] + r"\python.exe"; subprocess.run((x, 'C:\\...\\manual_toolbox_install.py'), capture_output=True, text=True, shell=True, timeout=1000 )
# then restart

from subprocess_call import subprocess_call
import os 

pythonPath = "C:\\ ...\\custom_environment_name\\python.exe"

def installToolbox(newExec: str):
    print("Installing Speckle Toolbox")
    whl_file = os.path.join(os.path.dirname(__file__), "speckle_toolbox-0.1-py3-none-any.whl" ) 
    subprocess_call([newExec, '-m','pip','install','--upgrade', '--force-reinstall', whl_file])
    return

def installDependencies(pythonExec: str):
    print("Installing dependencies")
    print(pythonExec)
    try:
        import pip
    except:
        getPipFilePath = os.path.join(os.path.dirname(__file__), "get_pip.py") 
        exec(open(getPipFilePath).read())

        # just in case the included version is old
        subprocess_call([pythonExec, "-m", "pip", "install", "--upgrade", "pip"])
    
    pkgVersion = "2.7.4" 
    pkgName = "specklepy"
    try:
        import specklepy 
    except Exception as e:
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
        print(f"Attempting to update specklepy to {pkgVersion}")
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
    return True

installToolbox(pythonPath)
installDependencies(pythonPath)


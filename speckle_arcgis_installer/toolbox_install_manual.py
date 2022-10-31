# MANUAL INSTALLATION: 
#   1. Clone the default ArcGIS Pro conda environment 
#       for 2.9.0: Project-> Python-> Manage Environments-> Clone Default
#       for 3.0.0: Project-> Package Manager-> Active Environment (Environment Manager)-> Clone arcgispro-py3
#   2. Change the path to your new environemnt Python.exe if necessary (in variable "pythonPath" below, line 13) 
#   3. Enter the location of 'toolbox_install_manual.py' in the following command and run this command in ArcGIS Python console (View -> Python Window)
#   import sysconfig; import subprocess; x = sysconfig.get_paths()['data'] + r"\python.exe"; subprocess.run((x, 'C:\\Users\\myusername\\Documents\\manual_toolbox_install.py'), capture_output=True, text=True, shell=True, timeout=1000 )
#   4. Restart ArcGIS Pro 

from subprocess_call import subprocess_call
import os 

pythonPath = os.getenv('APPDATA').replace("\\Roaming","") + r"\Local\ESRI\conda\envs\arcgispro-py3-speckle\python.exe"

def installToolbox(newExec: str):
    print("Installing Speckle Toolbox")
    whl_file = os.path.join(os.path.dirname(__file__), "speckle_toolbox-2.9.4-py3-none-any.whl" ) 
    subprocess_call([newExec, '-m','pip','install','--upgrade', '--force-reinstall', whl_file])
    return

def installDependencies(pythonExec: str, pkgName: str, pkgVersion: str):
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

installToolbox(pythonPath)
installDependencies(pythonPath, "specklepy", "2.9.0"  )
installDependencies(pythonPath, "panda3d", "1.10.11" )


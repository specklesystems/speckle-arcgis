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
    pythonExec = sysconfig.get_paths()['data'] + r"\python" # e.g. C:\Users\Kateryna\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone  # or: import site; site.getsitepackages()[0]
    #if sys.platform == "win32":
        #folder = [f for f in listdir(pythonExec + "\\Python\\envs")][0] # by default "arcgispro-py3"
        #pythonExec +=  "\\Python\\envs\\" + folder
    print(pythonExec) 

    if pythonExec.endswith(r"\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python"): 
        print("default env - need to clone")
        pythonExec = clone_env(pythonExec)
        return None 

    ## should be: %LOCALAPPDATA%\ESRI\conda\envs\arcgispro-py3-clone + python.exe, C:\Users\[UserName]\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone 
    # 
    #  + python.exe, C:\Users\[UserName]\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone
    # or default: %PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3  + python.exe,  C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3
    ## try: https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/installing-python-for-arcgis-pro.htm#ESRI_SECTION2_7FDA7FD13D724C51B442D8859F3A25A8

    return pythonExec

def clone_env(pythonExec_old: str): #"%PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3"
    # EVERYTHING HERE: https://support.esri.com/en/Technical-Article/000020560
    # https://developers.arcgis.com/python/guide/understanding-conda/
    #then https://support.esri.com/en/technical-article/000024206

    # https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#cloning-an-environment
    arcpy.AddMessage("Clone env")
    print("Clone env")
    winExec = r"%SystemRoot%\System32\cmd.exe"
    install_folder = r"%LOCALAPPDATA%\ESRI\conda\envs" 
    if not os.path.exists(install_folder): os.makedirs(install_folder)
    env_new_name = "arcgispro-py3-speckle-clone"
    # command: conda create --clone <environment to clone>  -p <path><new environment name>
    r'''
    trying:
x = subprocess.run( ("%SystemRoot%\\System32\\cmd.exe",  f"""conda activate %PROGRAMFILES%\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3
    conda create --clone %PROGRAMFILES%\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3 -p %LOCALAPPDATA%\\ESRI\\conda\\envs\\new_speckle_env"""),
    capture_output=True, text=True, shell=True, timeout=1000)

    shorter command to check (works but writes a strange file), e.g. 
Microsoft Windows [Version 10.0.18363.1556]
(c) 2019 Microsoft Corporation. All rights reserved.
C:\Users\Kateryna\Documents\ArcGIS\Projects\MyProject-test>"

x = subprocess.run( ('%SystemRoot%\\System32\\cmd.exe', 'conda', 'activate', '%PROGRAMFILES%\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3', ';', 'conda', 'list', '--explicit', '>', '%LOCALAPPDATA%\\ESRI\\conda\\envs\\spec-file-speckle.txt'), capture_output=True, text=True, shell=True, timeout=1000)
print(x)    

    trying with python exe (can't open file 'conda': [Errno 2] No such file or directory):
x = subprocess.run( ('C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe', 'conda', 'activate', 'C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3', ';', 'conda', 'list', '--explicit', '>', 'C:\\Users\Kateryna\\AppData\\Local\\ESRI\\conda\\envs\\spec-file-speckle.txt'), capture_output=True, text=True, shell=True, timeout=1000)
print(x)
CompletedProcess(args=('C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe', 'conda', 'activate', 'C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3', ';', 'conda', 'list', '--explicit', '>', 'C:\\Users\\Kateryna\\AppData\\Local\\ESRI\\conda\\envs\\spec-file-speckle.txt'), returncode=2, stdout='', 
stderr="C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe: can't open file 'conda': [Errno 2] No such file or directory\n")
    '''

    default_env = pythonExec_old.replace("py3\\python","py3") # + "\\" + 'arcgispro-py3'
    conda_exe = default_env.replace("envs\\arcgispro-py3","Scripts\\conda.exe")
    spec_file = install_folder + "\\def_env_spec.txt" 
    new_env = install_folder + "\\" + env_new_name  
    if not os.path.exists(new_env): 
        print(pythonExec_old)
        print(default_env)
        print(new_env)

        subprocess_call( [conda_exe, 'list', '--explicit', '>', spec_file] )
        subprocess_call( [conda_exe, 'create', '--prefix', new_env, '--file', spec_file] )
    #then: activate new_env

    #WORKS: subprocess.run( ('C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\Scripts\\conda.exe', 'list', '--explicit', '>', 'C:\\Users\Kateryna\\AppData\\Local\\ESRI\\conda\\envs\\spec-file-speckle.txt'), blabla )
    #print(x)
    
    #subprocess_call([f'bash -c "conda activate {default_env}; conda create --clone {default_env} -p {new_env}; conda activate {new_env}"']) #, shell=True)
    #subprocess_call(['bash -c "conda activate base; python -V"']) #, shell=True)
    
    #WORKS conda create --clone "%PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3" -p "%LOCALAPPDATA%\ESRI\conda\envs\arcgispro-py3-speckle-clone"
    # conda activate "%LOCALAPPDATA%\ESRI\conda\envs\arcgispro-py3-speckle-clone"
    #subprocess_call([pythonExec_old, "conda", "create", "--clone", default_env, "-p", new_env]) 
    #subprocess_call([pythonExec_old, "conda", "activate", new_env]) 
    r''' example from clone env 
    CompletedProcess(args=['C:\\Users\\Kateryna\\AppData\\Local\\ESRI\\conda\\envs\\arcgispro-py3-speckle-clone\\python', '-m', 'pip', 'install', 'specklepy==2.7.4'], 
    returncode=0, stdout='Collecting specklepy==2.7.4\n  Using cached specklepy
    '''

    r''' example from the default env
    CompletedProcess(args=['C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python', 'conda', 'create', '--clone', 
    'C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\arcgispro-py3', '-p', 
    '%LOCALAPPDATA%\\ESRI\\conda\\envs\\arcgispro-py3-speckle2-clone'], returncode=2, stdout='', 
    stderr="C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python: can't open file 'conda': [Errno 2] No such file or directory\n")
    '''

    r''' example2 from the default env
    CompletedProcess(args=['"C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python"', 'conda', 'create', '--clone',
         '"C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\arcgispro-py3"', '-p', '"%LOCALAPPDATA%\\ESRI\\conda\\envs\\arcgispro-py3-speckle2-clone"'], 
          returncode=1, stdout='', stderr='The filename, directory name, or volume label syntax is incorrect.\n')
    end
    start
    CompletedProcess(args=['"C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python"', 'conda', 'activate', 
        '"%LOCALAPPDATA%\\ESRI\\conda\\envs\\arcgispro-py3-speckle2-clone"'], 
        returncode=1, stdout='', stderr='The filename, directory name, or volume label syntax is incorrect.\n')
    '''
    
    r'''
import subprocess
import os
pythonExec_old = r"%PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python"
exect = r"C:\Users\Kateryna\AppData\Local\ESRI\conda\envs\arcgispro-py3-clone\python" 
install_folder = r"%LOCALAPPDATA%\ESRI\conda\envs" 
env_new_name = "arcgispro-py3-speckle2-clone"
default_env = pythonExec_old.replace("py3\\python","py3")

# characters 
pythonExec_old = '\"' + pythonExec_old + '\"'
exect = '\"' + exect + '\"'
default_env = '\"' + default_env + "\\" + 'arcgispro-py3\"'
new_env = '\"' + install_folder + "\\" + env_new_name + '\"'

print(exect)
print(default_env)
print(new_env)

args = (pythonExec_old, "conda", "create", "--clone", default_env, "-p", new_env)
result = subprocess.run(args, capture_output=True, text=True, shell=True, timeout=1000)
print(result)

    '''
    print("subprocess returned")
    #return pythonExec_old
    
    #TRYING WITH SPECS FILE
    # conda list --explicit > spec-file.txt
    #subprocess_call([winExec, "conda", "install", "--name", f{env_new_name}, "--file", f"{install_folder}\spec-file.txt"])
    #subprocess_call([install_folder, "conda", "activate", f"{env_new_name}"]) 
    #return install_folder + "\" + env_new_name

def setup():
    plugin_dir = os.path.dirname(__file__) 
    #print(plugin_dir) 
    pythonExec = get_python_path() # import numpy; import os; print(os.path.abspath(numpy.__file__)) 
    print(pythonExec)

    if pythonExec is None: 
        #arcpy.AddError("Pip not installed, setting up now")
        return False
    ##################### install dependencies ###################################
    
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
        import specklepy 
        # C:\Users\Kateryna\AppData\Roaming\Python\Python37\site-packages\specklepy\__init__.py 
    except Exception as e:
        arcpy.AddMessage("Specklepy not installed")
        print("Specklepy not installed")
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
    
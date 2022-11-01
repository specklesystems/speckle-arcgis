### Manual installation

1. Download present "speckle_arcgis_installer" folder
2. Clone the default ArcGIS Pro conda environment and restart ArcGIS Pro
       - for 2.9.0: Project-> Python-> Manage Environments-> Clone Default
       - for 3.0.0: Project-> Package Manager-> Active Environment (Environment Manager)-> Clone arcgispro-py3
3. Change the path to your new environemnt Python.exe if necessary (variable "pythonPath" in "toolbox_install_manual.py") 
4. Enter the location of 'toolbox_install_manual.py' in the following command and run this command in ArcGIS Python console (View -> Python Window)

```python
import sysconfig; import subprocess; x = sysconfig.get_paths()['data'] + r"\python.exe"; subprocess.run((x, 'C:\\Users\\pathToFolder\\speckle_arcgis_installer\\toolbox_install_manual.py'), capture_output=True, text=True, shell=True, timeout=1000 )
```


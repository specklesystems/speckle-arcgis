### Manual installation

1. From the [latest release](https://github.com/specklesystems/speckle-arcgis/releases) download the whl file and the source code zip, unzip and locate the subfolder "speckle_arcgis_installer" on your machine and place whl file in it. 
2. Clone the default ArcGIS Pro conda environment (or set the one you use, except the default one) and restart ArcGIS Pro
       - for 3.0.0: Project-> Package Manager-> Active Environment (Environment Manager)-> Clone arcgispro-py3
3. Adjust the path to your new environment python executable (variable "pythonPath" in "speckle_arcgis_installer/toolbox_install_manual.py") 
4. Enter the location of 'toolbox_install_manual.py' in the following command and run this command in ArcGIS Python console (View -> Python Window)

```python
import sysconfig; import subprocess; x = sysconfig.get_paths()['data'] + r"\python.exe"; subprocess.run((x, 'C:\\Users\\pathToFolder\\speckle_arcgis_installer\\toolbox_install_manual.py'), capture_output=True, text=True, shell=True, timeout=1000 )
```


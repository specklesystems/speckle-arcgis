# to build an installer: run cmd from this folder or use terminal: "%PROGRAMFILES%\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" 
# 
# python patch_version 2.x.x 
# C:\\Users\\username\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\setup.py sdist bdist_wheel 
# copy .whl to "speckle_arcgis_installer" 

# ref: https://pro.arcgis.com/en/pro-app/2.8/arcpy/geoprocessing_and_python/distributing-python-modules.htm

import os 
from setuptools import setup 


def read(fname): 
    return open(os.path.join(os.path.dirname(__file__), fname)).read() 
 
setup(name='speckle_toolbox', 
      version='0.1',
      author='SpeckleSystems',
      description=("Example for extending geoprocessing through Python modules"),
      long_description=read('Readme.md'),
      python_requires='~=3.3',
      packages=['speckle_toolbox'], 
      package_data={'speckle_toolbox':['esri/toolboxes/*',  
                  'esri/arcpy/*', 
                  'esri/help/gp/*', 'esri/help/gp/toolboxes/*', 'esri/help/gp/messages/*',
                  'esri/toolboxes/*','esri/toolboxes/speckle/*',
                  'esri/toolboxes/speckle/converter/*', 'esri/toolboxes/speckle/converter/geometry/*', 'esri/toolboxes/speckle/converter/layers/*',
                  'esri/toolboxes/speckle/plugin_utils/*'] 
                  }, 
      )

# then to install in ArcGIS:
# import sysconfig; import subprocess; x = sysconfig.get_paths()['data'] + r"\python.exe"; subprocess.run((x, '-m','pip', 'install', 'C:\\Users\\username\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\dist\\foo-0.1-py3-none-any.whl'), capture_output=True, text=True, shell=True, timeout=1000 )
# to uninstall: 
# "C:\\Users\\username\\AppData\\Local\\ESRI\\conda\\envs\\arcgispro-py3-speckle\\python.exe" -m pip uninstall C:\\Users\\username\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\dist\\foo-0.1-py3-none-any.whl

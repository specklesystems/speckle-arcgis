import os 
from setuptools import setup 

# https://pro.arcgis.com/en/pro-app/2.8/arcpy/geoprocessing_and_python/distributing-python-modules.htm

def read(fname): 
    return open(os.path.join(os.path.dirname(__file__), fname)).read() 
 
setup(name='foo', 
      version='0.1',
      author='SpeckleSystems',
      description=("Example for extending geoprocessing through Python modules"),
      long_description=read('Readme.txt'),
      python_requires='~=3.3',
      packages=['foo'], 
      package_data={'foo':['esri/toolboxes/*',  
                  'esri/arcpy/*', 
                  'esri/help/gp/*', 'esri/help/gp/toolboxes/*', 'esri/help/gp/messages/*',
                  'esri/toolboxes/*','esri/toolboxes/speckle/*',
                  'esri/toolboxes/speckle/converter/*', 'esri/toolboxes/speckle/converter/geometry/*', 'esri/toolboxes/speckle/converter/layers/*',
                  'esri/toolboxes/speckle/plugin_utils/*'] 
                  }, 
      )

# to build an installer: run cmd from this folder:
# "%PROGRAMFILES%\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe"  C:\\Users\\Kateryna\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\setup.py sdist bdist_wheel 

# then to install in ArcGIS:
# import sysconfig; import subprocess; x = sysconfig.get_paths()['data'] + r"\python.exe"; subprocess.run((x, '-m','pip', 'install', 'C:\\Users\\Kateryna\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\dist\\foo-0.1-py3-none-any.whl'), capture_output=True, text=True, shell=True, timeout=1000 )
# to uninstall: 
# "C:\\Users\\Kateryna\\AppData\\Local\\ESRI\\conda\\envs\\arcgispro-py3-speckle\\python.exe" -m pip uninstall C:\\Users\\Kateryna\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\dist\\foo-0.1-py3-none-any.whl

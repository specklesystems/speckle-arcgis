# to build an installer: run cmd from this folder or use terminal: "%PROGRAMFILES%\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe"
#
# 1) python patch_version.py 2.x.x
# 2) python setup.py sdist bdist_wheel   #C:\\Users\\username\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\setup.py sdist bdist_wheel
# copy .whl from "dist" to "speckle_arcgis_installer"

# ref: https://pro.arcgis.com/en/pro-app/2.8/arcpy/geoprocessing_and_python/distributing-python-modules.htm

import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="speckle_toolbox",
    author="SpeckleSystems",
    version="0.0.99",
    author_email="connectors@speckle.systems",
    url="https://speckle.systems/",
    description=("Example for extending geoprocessing through Python modules"),
    long_description=read("Readme.md"),
    python_requires="~=3.3",
    setup_requires=["wheel"],
    packages=["speckle_toolbox"],
    package_data={
        "speckle_toolbox": [
            "esri/arcpy/*",
            "esri/help/gp/*",
            "esri/help/gp/toolboxes/*",
            "esri/help/gp/messages/*",
            "esri/toolboxes/*",
            "esri/toolboxes/speckle/*",
            "esri/toolboxes/speckle/speckle/*",
            "esri/toolboxes/speckle/speckle/converter/*",
            "esri/toolboxes/speckle/speckle/converter/features/*",
            "esri/toolboxes/speckle/speckle/converter/geometry/*",
            "esri/toolboxes/speckle/speckle/converter/layers/*",
            "esri/toolboxes/speckle/speckle/plugin_utils/*",
            "esri/toolboxes/speckle/speckle/utils/*",
            "esri/toolboxes/speckle/specklepy_qt_ui/*",
            "esri/toolboxes/speckle/specklepy_qt_ui/qt_ui/*",
            "esri/toolboxes/speckle/specklepy_qt_ui/qt_ui/ui/*",
            "esri/toolboxes/speckle/specklepy_qt_ui/qt_ui/utils/*",
            "esri/toolboxes/speckle/specklepy_qt_ui/qt_ui/utils/assets/*",
            "esri/toolboxes/speckle/ui_widgets/*",
        ]
    },
)

# then to install in ArcGIS:
# import sysconfig; import subprocess; x = sysconfig.get_paths()['data'] + r"\python.exe"; subprocess.run((x, '-m','pip', 'install', 'C:\\Users\\username\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\dist\\foo-0.1-py3-none-any.whl'), capture_output=True, text=True, shell=True, timeout=1000 )
# to uninstall:
# "C:\\Users\\username\\AppData\\Local\\ESRI\\conda\\envs\\arcgispro-py3-speckle\\python.exe" -m pip uninstall C:\\Users\\username\\Documents\\00_Speckle\\GitHub\\speckle-arcgis\\dist\\foo-0.1-py3-none-any.whl

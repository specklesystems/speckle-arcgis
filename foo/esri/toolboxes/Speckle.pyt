
from speckle.plugin_utils.installDependencies import setup

if setup() == True: #only start the plugin if restart is non needed
    from speckle.speckle_arcgis import *
else: 
    from speckle.plugin_utils.install_message import *
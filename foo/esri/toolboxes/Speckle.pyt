
from speckle.plugin_utils.installDependencies import setup

# only activation of speckle env (if default) / or installation of packages into current dev
if setup() == True: 
    from speckle.speckle_arcgis import * # only start the plugin if restart is non needed
else: 
    from speckle.plugin_utils.install_message import * # if restart is needed
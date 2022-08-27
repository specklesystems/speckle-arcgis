# -*- coding: utf-8 -*-

import arcpy

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Speckle Toolbox"
        self.alias = "speckle_toolbox_"  
        self.tools = [Speckle]    

class Speckle(object):
    def __init__(self):
        print("________________reset_______________")   
        self.label       = "Speckle"
        self.description = ""
        
    def getParameterInfo(self):

        message = arcpy.Parameter(
            displayName="",
            name="message",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        message.value = f""" 
    ArcGIS Pro Python environment is set to Default. 
    Speckle has created and/or activated a new virtual environment. 
    Please restart ArcGIS Pro for changes to take effect.
    """
        parameters = [message]
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return 

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters): 
        return
    
    
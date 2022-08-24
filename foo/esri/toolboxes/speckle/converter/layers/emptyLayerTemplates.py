def createGroupLayer() -> str: 
  return r"""
    {
      "type" : "CIMLayerDocument",
      "version" : "2.9.0",
      "build" : 32739,
      "layers" : [
        "CIMPATH=map/new_group_layer2.xml"
      ],
      "layerDefinitions" : [
        {
          "type" : "CIMGroupLayer",
          "name" : "TestGroupLayer",
          "uRI" : "CIMPATH=map/new_group_layer2.xml",
          "sourceModifiedTime" : {
            "type" : "TimeInstant",
            "start" : 978307200000
          },
          "metadataURI" : "CIMPATH=Metadata/519714a81d3f97d29d02d2f4b2ee1a33.xml",
          "useSourceMetadata" : true,
          "description" : "New Group Layer",
          "layerElevation" : {
            "type" : "CIMLayerElevationSurface",
            "mapElevationID" : "{A89C500E-DBD6-4093-87B5-2D898169D9E4}"
          },
          "layerType" : "Operational",
          "showLegends" : true,
          "visibility" : true,
          "displayCacheType" : "Permanent",
          "maxDisplayCacheAge" : 5,
          "showPopups" : true,
          "serviceLayerID" : -1,
          "refreshRate" : -1,
          "refreshRateUnit" : "esriTimeUnitsSeconds",
          "blendingMode" : "Alpha",
          "allowDrapingOnIntegratedMesh" : true
        }
      ],
      "binaryReferences" : [
        {
          "type" : "CIMBinaryReference",
          "uRI" : "CIMPATH=Metadata/519714a81d3f97d29d02d2f4b2ee1a33.xml",
          "data" : "<?xml version=\"1.0\"?>\r\n<metadata xml:lang=\"en\"><Esri><CreaDate>20220808</CreaDate><CreaTime>21203100</CreaTime><ArcGISFormat>1.0</ArcGISFormat><SyncOnce>TRUE</SyncOnce></Esri><dataIdInfo><idCitation><resTitle>New Group Layer</resTitle></idCitation><idAbs>New Group Layer</idAbs><idCredit></idCredit><idPurp></idPurp><resConst><Consts><useLimit></useLimit></Consts></resConst></dataIdInfo></metadata>\r\n"
        }
      ],
      "elevationSurfaces" : [
        {
          "type" : "CIMMapElevationSurface",
          "elevationMode" : "BaseGlobeSurface",
          "name" : "Ground",
          "verticalExaggeration" : 1,
          "mapElevationID" : "{A89C500E-DBD6-4093-87B5-2D898169D9E4}",
          "color" : {
            "type" : "CIMRGBColor",
            "values" : [
              255,
              255,
              255,
              100
            ]
          },
          "surfaceTINShadingMode" : "Smooth",
          "visibility" : true,
          "expanded" : true
        }
      ],
      "rGBColorProfile" : "sRGB IEC61966-2.1",
      "cMYKColorProfile" : "U.S. Web Coated (SWOP) v2"
    }
    """

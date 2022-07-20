from specklepy.objects import Base
import arcpy 

from speckle.converter.geometry._init_ import convertToSpeckle

def featureToSpeckle(fieldnames, attr_list, f_shape, projectCRS: arcpy.SpatialReference, project: arcpy.mp.ArcGISProject, selectedLayer):
    print("___________Feature to Speckle____________")
    b = Base()
    data = arcpy.Describe(selectedLayer.dataSource)
    layer_sr = data.spatialReference # if sr.type == "Projected":
    geomType = data.shapeType #Polygon, Point, Polyline, Multipoint, MultiPatch
    featureType = data.featureType # Simple,SimpleJunction,SimpleJunction,ComplexEdge,Annotation,CoverageAnnotation,Dimension,RasterCatalogItem 

    print(layer_sr.name)
    print(projectCRS.name)

    #apply transformation if needed
    if layer_sr.name != projectCRS.name:
        tr0 = tr1 = tr2 = None
        transformations = arcpy.ListTransformations(layer_sr, projectCRS)
        if len(transformations) == 0:
            midSr = arcpy.SpatialReference("GCS_WGS_1984") 
            tr1 = arcpy.ListTransformations(layer_sr, midSr)[0]
            tr2 = arcpy.ListTransformations(midSr, projectCRS)[0]
        else: 
            # choose equation based instead of file-based/grid-based method, 
            # to be consistent with QGIS: https://desktop.arcgis.com/en/arcmap/latest/map/projections/choosing-an-appropriate-transformation.htm
            selecterTr = {}
            for tr in transformations:
                if "NTv2" not in tr and "NADCON" not in tr: 
                    set1 = set( layer_sr.name.split("_") + projectCRS.name.split("_") )
                    set2 = set( tr.split("_") )
                    diff = len( set(set1).symmetric_difference(set2) )
                    selecterTr.update({tr: diff})
            selecterTr = dict(sorted(selecterTr.items(), key=lambda item: item[1]))
            tr0 = list(selecterTr.keys())[0]

        if geomType != "Point" and geomType != "Polyline" and geomType != "Polygon" and geomType != "Multipoint":
            print(geomType)
            arcpy.AddWarning("Unsupported or invalid geometry in layer " + selectedLayer.name)

        # reproject geometry using chosen transformstion(s)
        if tr0 is not None:
            ptgeo1 = f_shape.projectAs(projectCRS, tr0)
            f_shape = ptgeo1
        else:
            ptgeo1 = f_shape.projectAs(midSr, tr1)
            ptgeo2 = ptgeo1.projectAs(projectCRS, tr2)
            f_shape = ptgeo2
        print(f_shape)

    # Convert geometry
    try:
        geom = convertToSpeckle(f_shape, selectedLayer, geomType, featureType)
        if geom is not None:
            b["geometry"] = geom
    except Exception as error:
        arcpy.AddError("Error converting geometry: " + str(error))

    print(attr_list)
    print(fieldnames)
    for i, name in enumerate(fieldnames):
        corrected = name.replace("/", "_").replace(".", "-")
        if corrected == "id": corrected = "applicationId"
        f_val = attr_list[i] #str()
        b[corrected] = f_val
    print("_____________________")
    return b

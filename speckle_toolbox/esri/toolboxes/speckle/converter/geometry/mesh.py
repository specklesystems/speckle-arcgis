from typing import List
import arcpy

from specklepy.objects.geometry import Mesh

import shapefile
from shapefile import TRIANGLE_STRIP, TRIANGLE_FAN
from speckle.converter.layers.utils import get_scale_factor

def meshToNative(meshes: List[Mesh], path: str):
    """Converts a Speckle Mesh to MultiPatch. Currently UNSUPPORTED"""
    #print("06___________________Mesh to Native")
    #print(mesh)
    #print(mesh.units)
    w = shapefile.Writer(path) 
    w.field('speckleType', 'C')

    shapes = []
    for mesh in meshes:
        scale = get_scale_factor(mesh.units)

        
        if len(mesh.faces) % 4 == 0 and mesh.faces[0] == 0:
            

            parts_list = []
            types_list = []
            count = 0 # sequence of vertex (not of flat coord list) 
            for f in mesh.faces:
                try:
                    if mesh.faces[count] == 0 or mesh.faces[count] == 3: # only handle triangles
                        f1 = [ scale*mesh.vertices[mesh.faces[count+1]*3], scale*mesh.vertices[mesh.faces[count+1]*3+1], scale*mesh.vertices[mesh.faces[count+1]*3+2] ]
                        f2 = [ scale*mesh.vertices[mesh.faces[(count+2)]*3], scale*mesh.vertices[mesh.faces[(count+2)]*3+1], scale*mesh.vertices[mesh.faces[(count+2)]*3+2] ]
                        f3 = [ scale*mesh.vertices[mesh.faces[(count+3)]*3], scale*mesh.vertices[mesh.faces[(count+3)]*3+1], scale*mesh.vertices[mesh.faces[(count+3)]*3+2] ]
                        parts_list.append([ f1, f2, f3 ])
                        types_list.append(TRIANGLE_FAN)
                        count += 4
                    else: 
                        count += mesh.faces[count+1]
                except: break
            w.multipatch(parts_list, partTypes=types_list ) # one type for each part
            w.record('displayMesh')
            
        else: print("not triangulated mesh")

        #shape = None
        #rows = arcpy.da.SearchCursor(path + mesh.id, 'Shape@')
        #for r in rows:
        #    if r is not None: shape = r

    w.close()

    return path

def rasterToMesh(vertices, faces, colors):
    mesh = Mesh.create(vertices, faces, colors)
    mesh.units = "m"
    return mesh

from typing import List, Optional
from specklepy.objects.base import Base

try: 
    from speckle.speckle.converter.layers.CRS import CRS
except:
    from speckle_toolbox.esri.toolboxes.speckle.speckle.converter.layers.CRS import CRS



class Layer(Base, chunkable={"elements": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name: Optional[str] = None,
        crs: Optional[CRS] = None,
        datum: Optional[CRS] = None,
        elements: List[Base] = [],
        layerType: str = "None",
        geomType: str = "None",
        renderer: dict = {},
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.datum = datum
        self.collectionType = layerType
        self.elements = elements
        self.geomType = geomType
        self.renderer = renderer 

class VectorLayer(Base, chunkable={"elements": 100}):
    """A GIS Vector Layer"""

    def __init__(
        self,
        name: Optional[str] = None,
        crs: Optional[CRS] = None,
        datum: Optional[CRS] = None,
        elements: List[Base] = [],
        layerType: str = "None",
        geomType: str = "None",
        renderer: dict = {},
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.datum = datum
        self.collectionType = layerType
        self.elements = elements
        self.geomType = geomType
        self.renderer = renderer 

class RasterLayer(Base, chunkable={"elements": 100}):
    """A GIS Raster Layer"""

    def __init__(
        self,
        name: Optional[str] = None,
        crs: Optional[CRS] =None,
        rasterCrs: Optional[CRS] = None,
        elements: List[Base] = [],
        layerType: str = "None",
        geomType: str = "None",
        renderer: dict = {},
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.rasterCrs = rasterCrs
        self.collectionType = layerType
        self.elements = elements
        self.geomType = geomType
        self.renderer = renderer 
    
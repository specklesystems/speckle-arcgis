from typing import List, Optional
from specklepy.objects.base import Base

from speckle.converter.layers.CRS import CRS



class Layer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name: Optional[str] = None,
        crs: Optional[CRS] = None,
        datum: Optional[CRS] = None,
        features: List[Base] = [],
        layerType: str = "None",
        geomType: str = "None",
        renderer: dict = {},
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.datum = datum
        self.type = layerType
        self.features = features
        self.geomType = geomType
        self.renderer = renderer 

class VectorLayer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name: Optional[str] = None,
        crs: Optional[CRS] = None,
        datum: Optional[CRS] = None,
        features: List[Base] = [],
        layerType: str = "None",
        geomType: str = "None",
        renderer: dict = {},
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.datum = datum
        self.type = layerType
        self.features = features
        self.geomType = geomType
        self.renderer = renderer 

class RasterLayer(Base, chunkable={"features": 100}):
    """A GIS Layer"""

    def __init__(
        self,
        name=None,
        crs=None,
        rasterCrs=None,
        features: List[Base] = [],
        layerType: str = "None",
        geomType: str = "None",
        renderer: dict = {},
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.crs = crs
        self.rasterCrs = rasterCrs
        self.type = layerType
        self.features = features
        self.geomType = geomType
        self.renderer = renderer 
    
import math
from specklepy.objects.geometry import Point

def pointToSpeckle(pt, feature, layer):
  
    """Converts a QgsPoint to Speckle"""
    # when unset, z() returns "nan"
    #print(pt) # 4.9046319 52.3592043 NaN NaN
    x = pt.X
    y = pt.Y
    if pt.Z: z = pt.Z 
    else: z = 0
    specklePoint = Point()
    specklePoint.x = x
    specklePoint.y = y
    specklePoint.z = z
    '''
    col = featureColorfromNativeRenderer(feature, layer)
    specklePoint['displayStyle'] = {}
    specklePoint['displayStyle']['color'] = col
    '''
    return specklePoint

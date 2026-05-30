import ee

def initialize_gee():
    ee.Initialize(project='geoacces-482711') 

BAND_MAP = {
    'L5': {'R':'SR_B3','G':'SR_B2','B':'SR_B1','NIR':'SR_B4','SWIR1':'SR_B5','SWIR2':'SR_B7'},
    'L7': {'R':'SR_B3','G':'SR_B2','B':'SR_B1','NIR':'SR_B4','SWIR1':'SR_B5','SWIR2':'SR_B7'},
    'L8': {'R':'SR_B4','G':'SR_B3','B':'SR_B2','NIR':'SR_B5','SWIR1':'SR_B6','SWIR2':'SR_B7'},
    'L9': {'R':'SR_B4','G':'SR_B3','B':'SR_B2','NIR':'SR_B5','SWIR1':'SR_B6','SWIR2':'SR_B7'},
}

COLLECTION_IDS = {
    'L5': 'LANDSAT/LT05/C02/T1_L2',
    'L7': 'LANDSAT/LE07/C02/T1_L2',
    'L8': 'LANDSAT/LC08/C02/T1_L2',
    'L9': 'LANDSAT/LC09/C02/T1_L2',
}

MISSION_PRIORITY = {
    year: (
        ['L9', 'L8'] if year >= 2021 else
        ['L8']       if year >= 2013 else
        ['L5']       if year <= 2012 else
        []
    )
    for year in range(1990, 2026)
}

def scale_l2(image):
    return image.multiply(0.0000275).add(-0.2)

def rename_bands(image, mission_key):
    bm = BAND_MAP[mission_key]
    return image.select(list(bm.values())).rename(['R','G','B','NIR','SWIR1','SWIR2'])

def get_annual_composite(year, aoi, preferred_missions=None):
    missions = preferred_missions or MISSION_PRIORITY.get(year, ['L8'])
    collections = []
    used_missions = []

    for mission in missions:
        col_id = COLLECTION_IDS.get(mission)
        if not col_id:
            continue
        col = (
            ee.ImageCollection(col_id)
            .filterDate(f'{year}-01-01', f'{year}-12-31')
            .filterBounds(aoi)
            .filter(ee.Filter.lt('CLOUD_COVER', 30))
            .map(scale_l2)
            .map(lambda img, m=mission: rename_bands(img, m))
        )
        size = col.size().getInfo()
        if size > 0:
            collections.append(col)
            used_missions.append(f"{mission}({size})")

    if not collections:
        return None, []

    merged = collections[0]
    for c in collections[1:]:
        merged = merged.merge(c)

    composite = merged.median().clip(aoi)
    return composite, used_missions

def apply_visualization(image, combo):
    vis_map = {
        'Natural Color':   {'bands': ['R','G','B'],       'min': 0.0, 'max': 0.3},
        'False Color NIR': {'bands': ['NIR','R','G'],     'min': 0.0, 'max': 0.4},
        'SWIR Composite':  {'bands': ['SWIR1','NIR','R'], 'min': 0.0, 'max': 0.5},
        'NDVI':            {'bands': ['NIR','R','G'],     'min':-0.2, 'max': 0.8},
        'NDWI':            {'bands': ['G','NIR','R'],     'min':-0.3, 'max': 0.5},
    }
    params = vis_map.get(combo, vis_map['Natural Color'])
    return image.select(params['bands']), params
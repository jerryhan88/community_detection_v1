import os.path as opath
import pickle
import numpy as np
from geopy.distance import VincentyDistance
from shapely.ops import cascaded_union
from shapely.geometry import Polygon
from pykml import parser
#
from __util_logger import get_logger
from __path_organizer import ef_dpath, pf_dpath

logger = get_logger()
NORTH, EAST, SOUTH, WEST = 0, 90, 180, 270
ZONE_UNIT_KM = 0.5


xConsiderDist = [
                    'North-Eastern Islands',
                    'Tuas View Extension',
                    'Jurong Island And Bukom',
                    'Southern Group',
                    'Semakau',
                    'Sudong',
                    'Pulau Seletar',
                 ]


def get_districtPoly():
    poly_fpath_PKL = opath.join(pf_dpath, 'DistrictsPolygon.pkl')
    if not opath.exists(poly_fpath_PKL):
        distPoly = {}
        kml_fpath = opath.join(ef_dpath, 'MP14_SUBZONE_WEB_PL.kml')
        with open(kml_fpath) as f:
            kml_doc = parser.parse(f).getroot().Document
        for pm in kml_doc.Folder.Placemark:
            str_coords = str(pm.MultiGeometry.Polygon.outerBoundaryIs.LinearRing.coordinates)
            poly_coords = []
            for l in ''.join(str_coords.split()).split(',0')[:-1]:
                lng, lat = map(eval, l.split(','))
                poly_coords.append([lat, lng])
            district_name = str(pm.name).title()
            if "'S" in district_name:
                district_name = district_name.replace("'S", "'s")
            if "S'Pore" in district_name:
                district_name = district_name.replace("S'Pore", "S'pore")
            if district_name in xConsiderDist:
                continue
            distPoly[district_name] = poly_coords
        with open(poly_fpath_PKL, 'wb') as fp:
            pickle.dump(distPoly, fp)
    else:
        with open(poly_fpath_PKL, 'rb') as fp:
            distPoly = pickle.load(fp)
    #
    return distPoly

def get_sgBorder():
    sgBorder_fpath = opath.join(pf_dpath, 'sgBorderPolygon.pkl')
    if opath.exists(sgBorder_fpath):
        with open(sgBorder_fpath, 'rb') as fp:
            sgBorder = pickle.load(fp)
        return sgBorder
    #
    distPoly = get_districtPoly()
    sgBorderPolys = cascaded_union([Polygon(poly) for _, poly in distPoly.items()])
    sgBorder = [np.array(poly.coords).tolist() for poly in sgBorderPolys.boundary]
    with open(sgBorder_fpath, 'wb') as fp:
        pickle.dump(sgBorder, fp)
    #
    return sgBorder

def get_sgGrid():
    sgGrid_fpath = opath.join(pf_dpath, 'sgGrid(%.1fkm).pkl'% ZONE_UNIT_KM)
    if opath.exists(sgGrid_fpath):
        with open(sgGrid_fpath, 'rb') as fp:
            lats, lngs = pickle.load(fp)
        return lats, lngs
    #
    sgBorder = get_sgBorder()
    min_lng, max_lng = 1e400, -1e400
    min_lat, max_lat = 1e400, -1e400
    for poly in sgBorder:
        for lat, lng in poly:
            if lng < min_lng:
                min_lng = lng
            if lng > max_lng:
                max_lng = lng
            if lat < min_lat:
                min_lat = lat
            if lat > max_lat:
                max_lat = lat
    #
    mover = VincentyDistance(kilometers=ZONE_UNIT_KM)
    #
    lats, lngs = [], []
    lat = min_lat
    while lat < max_lat:
        lats += [lat]
        p0 = [lat, min_lng]
        moved_point = mover.destination(point=p0, bearing=NORTH)
        lat = moved_point.latitude
    lon = min_lng
    while lon < max_lng:
        lngs += [lon]
        p0 = [min_lat, lon]
        moved_point = mover.destination(point=p0, bearing=EAST)
        lon = moved_point.longitude
    lats.sort()
    lngs.sort()
    #
    with open(sgGrid_fpath, 'wb') as fp:
        pickle.dump([lats, lngs], fp)
    return lats, lngs

# import webbrowser
# import folium
# import geopandas as gpd
# def get_sgPoints():
#     ofpath = opath.join(dpath['geo'], 'sgPoints.pkl')
#     sgPoints = None
#     if opath.exists(ofpath):
#         with open(ofpath, 'rb') as fp:
#             sgPoints = pickle.load(fp)
#         return sgPoints
#     ifpath = opath.join(dpath['geo'], 'singapore_osm_point.geojson')
#     df = gpd.read_file(ifpath)
#     sgPoints = []
#     sgMainBorder = Polygon(get_sgMainBorder())
#     for i in xrange(len(df)):
#         if not df.loc[i, 'geometry'].within(sgMainBorder):
#             continue
#         point_info = {}
#         for cn in df.columns:
#             if not df.loc[i, cn]:
#                 continue
#             point_info[cn] = df.loc[i, cn]
#         sgPoints += [point_info]
#     with open(ofpath, 'wb') as fp:
#         pickle.dump(sgPoints, fp)
#     return sgPoints
#
#
# def get_sgPolygons():
#     ofpath = opath.join(dpath['geo'], 'sgPolygons.pkl')
#     sgPolygons = None
#     if opath.exists(ofpath):
#         with open(ofpath, 'rb') as fp:
#             sgPolygons = pickle.load(fp)
#         return sgPolygons
#     ifpath = opath.join(dpath['geo'], 'singapore_osm_polygon.geojson')
#     df = gpd.read_file(ifpath)
#     sgPolygons = []
#     sgMainBorder = Polygon(get_sgMainBorder())
#     for i in xrange(len(df)):
#         if not df.loc[i, 'geometry'].within(sgMainBorder):
#             continue
#         poly_info = {}
#         for cn in df.columns:
#             if not df.loc[i, cn]:
#                 continue
#             poly_info[cn] = df.loc[i, cn]
#         sgPolygons += [poly_info]
#     with open(ofpath, 'wb') as fp:
#         pickle.dump(sgPolygons, fp)
#     return sgPolygons
#
#
# def find_aZone_points(zi, zj, zPoly, sgPoints):
#     try:
#         logger.info('handle %d %d; points' % (zi, zj))
#         ofpath = opath.join(dpath['zonePoints'], 'zonePoints-zi(%d)zj(%d).pkl' % (zi, zj))
#         if opath.exists(ofpath):
#             return None
#         aZone_points = []
#         for point_info in sgPoints:
#             if point_info['geometry'].within(zPoly):
#                 aZone_points += [dict(point_info)]
#         with open(ofpath, 'wb') as fp:
#             pickle.dump(aZone_points, fp)
#     except Exception as _:
#         import sys
#         with open('%s_%d_%d.txt' % (sys.argv[0], zi, zj), 'w') as f:
#             f.write(format_exc())
#         raise
#
#
# def find_aZone_polygons(zi, zj, zPoly, sgPolygons):
#     try:
#         logger.info('handle %d %d; polygons' % (zi, zj))
#         ofpath = opath.join(dpath['zonePolygons'], 'zonePolygons-zi(%d)zj(%d).pkl' % (zi, zj))
#         if opath.exists(ofpath):
#             return None
#         aZone_polygons = []
#         for poly_info in sgPolygons:
#             if poly_info['geometry'].intersects(zPoly) or poly_info['geometry'].within(zPoly):
#                 aZone_polygons += [dict(poly_info)]
#         with open(ofpath, 'wb') as fp:
#             pickle.dump(aZone_polygons, fp)
#     except Exception as _:
#         import sys
#         with open('%s_%d_%d.txt' % (sys.argv[0], zi, zj), 'w') as f:
#             f.write(format_exc())
#         raise
#
#
# def classify_aZone_objects(processorID, NUM_WORKERS=11):
#     lons, lats = get_sgGrid()
#     sgPoints, sgPolygons = get_sgPoints(), get_sgPolygons()
#     i = 0
#     for zi in xrange(len(lons) - 1):
#         for zj in xrange(len(lats) - 1):
#             i += 1
#             if i % NUM_WORKERS != processorID:
#                 continue
#             rightTop = (lons[zi + 1], lats[zj + 1])
#             rightBottom = (lons[zi + 1], lats[zj])
#             leftBottom = (lons[zi], lats[zj])
#             leftTop = (lons[zi], lats[zj + 1])
#             zPoly = Polygon([rightTop, rightBottom, leftBottom, leftTop])
#             find_aZone_points(zi, zj, zPoly, sgPoints)
#             find_aZone_polygons(zi, zj, zPoly, sgPolygons)
#
#
# def viz_interactionHotspots(hotspots, path=None):
#     lons, lats = get_sgGrid()
#     lon0, lon1 = lons[0], lons[-1]
#     lat0, lat1 = lats[0], lats[-1]
#     lonC, latC = (lon0 + lon1) / 2.0, (lat0 + lat1) / 2.0
#     #
#     map_osm = folium.Map(location=[latC, lonC], zoom_start=12)
#     for zi, zj, w in hotspots:
#         lon0, lat0 = lons[zi], lats[zj]
#         lon1, lat1 = lons[zi + 1], lats[zj + 1]
#         lonC, latC = (lon0 + lon1) / 2.0, (lat0 + lat1) / 2.0
#         folium.Marker((latC, lonC), popup='zid (%d, %d): %.2f' % (zi, zj, w),
#                       icon=folium.Icon(color='red')
#                       ).add_to(map_osm)
#     for lon in lons:
#         sx, sy, ex, ey = lon, lats[0], lon, lats[-1]
#         map_osm.add_children(folium.PolyLine(locations=[(sy, sx), (ey, ex)], weight=1.0))
#     for lat in lats:
#         sx, sy, ex, ey = lons[0], lat, lons[-1], lat
#         map_osm.add_children(folium.PolyLine(locations=[(sy, sx), (ey, ex)], weight=1.0))
#     if path == None:
#         fpath = opath.join(opath.join(opath.dirname(__file__), 'test.html'))
#         map_osm.save(fpath)
#         html_url = 'file://%s' % fpath
#         webbrowser.get('safari').open_new(html_url)
#     else:
#         map_osm.save(path)


if __name__ == '__main__':
    # get_sgGrid()
    get_sgBorder()

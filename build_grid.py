"""운날 격자 오행 파일 생성 — docs/unnal/04_데이터_스펙.md 1부

OpenStreetMap 한국 추출본(Geofabrik south-korea-latest.osm.pbf) → 약 200m 래스터에 오행 원재료를 쌓고
반경 500m로 흐리게 한 뒤, geohash 6자리 셀마다 오행 분포 P[5](합 255)를 기록합니다.

  목: 공원·숲·풀밭·가로수        화: 상점·음식점·카페·상업지
  토: 농지·운동장·광장·주차장     금: 건물(층수 가중)·산업지·바위
  수: 하천·호수·저수지·습지·해안선·분수

사용:  python build_grid.py south-korea-latest.osm.pbf out/grid-v1.bin
라이선스: 결과 파일은 OSM 파생 데이터베이스이므로 ODbL. © OpenStreetMap contributors
"""
import sys, math, struct, json, hashlib, time
import numpy as np
import osmium
import shapely
from shapely import wkb as swkb
from scipy.ndimage import convolve

LAT0, LAT1, LON0, LON1 = 33.0, 38.75, 124.5, 132.0
DLAT, DLON = 0.0018, 0.00225           # 약 200m × 200m
ROWS = int(round((LAT1 - LAT0) / DLAT))
COLS = int(round((LON1 - LON0) / DLON))
EL = ['목', '화', '토', '금', '수']

raw = np.zeros((5, ROWS, COLS), dtype=np.float32)


def cell(lat, lon):
    r = int((lat - LAT0) / DLAT); c = int((lon - LON0) / DLON)
    if 0 <= r < ROWS and 0 <= c < COLS:
        return r, c
    return None


def add_point(e, lat, lon, v):
    rc = cell(lat, lon)
    if rc:
        raw[e, rc[0], rc[1]] += v


def area_class(t):
    lu, le, na, wa, am = t.get('landuse'), t.get('leisure'), t.get('natural'), t.get('waterway'), t.get('amenity')
    if le in ('park', 'garden', 'nature_reserve', 'dog_park') or lu in ('forest', 'grass', 'meadow', 'recreation_ground', 'village_green', 'orchard', 'cemetery') \
            or na in ('wood', 'scrub', 'grassland', 'heath'):
        return 0
    if na in ('water', 'wetland', 'bay') or lu in ('reservoir', 'basin') or wa in ('riverbank', 'dock') or t.get('water'):
        return 4
    if lu in ('retail', 'commercial'):
        return 1
    if lu in ('farmland', 'farmyard', 'allotments', 'greenfield', 'brownfield', 'construction') or le in ('pitch', 'stadium', 'track', 'sports_centre', 'playground') \
            or t.get('place') == 'square' or am == 'parking' or na in ('sand', 'beach'):
        return 2
    if lu in ('industrial', 'railway', 'military') or na in ('bare_rock', 'cliff', 'scree'):
        return 3
    return None


FIRE_AMENITY = {'restaurant', 'cafe', 'bar', 'pub', 'fast_food', 'food_court', 'nightclub', 'cinema', 'theatre', 'ice_cream', 'marketplace', 'karaoke_box'}
METAL_AMENITY = {'bank', 'atm', 'hospital', 'clinic', 'police', 'fire_station', 'post_office', 'townhall', 'courthouse', 'fuel', 'charging_station'}
EARTH_AMENITY = {'school', 'university', 'college', 'kindergarten'}


def poi_weight(t):
    am = t.get('amenity')
    if t.get('shop') or am in FIRE_AMENITY or t.get('tourism') in ('hotel', 'attraction'):
        return 1
    if am in METAL_AMENITY:
        return 3
    if am in EARTH_AMENITY:
        return 2
    if am == 'fountain':
        return 4
    return None


class H(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.wkb = osmium.geom.WKBFactory()
        self.n = 0

    def node(self, n):
        t = n.tags
        if not len(t):
            return
        e = poi_weight(t)
        if e is not None:
            add_point(e, n.location.lat, n.location.lon, 1.0)
        elif t.get('natural') == 'tree':
            add_point(0, n.location.lat, n.location.lon, 0.2)

    def way(self, w):
        t = w.tags
        wa, na = t.get('waterway'), t.get('natural')
        kind = None
        if wa in ('river', 'canal'): kind, e, k = 'line', 4, 6.0
        elif wa in ('stream', 'drain', 'ditch'): kind, e, k = 'line', 4, 2.5
        elif na == 'coastline': kind, e, k = 'line', 4, 4.0
        elif na == 'tree_row': kind, e, k = 'line', 0, 1.0
        elif t.get('surface') in ('ground', 'dirt', 'sand', 'gravel', 'unpaved') and t.get('highway'): kind, e, k = 'line', 2, 0.5
        if kind is None:
            return
        try:
            pts = [(nd.location.lat, nd.location.lon) for nd in w.nodes]
        except osmium.InvalidLocationError:
            return
        for (a, b), (c, d) in zip(pts, pts[1:]):
            L = math.hypot((c - a) * 111.0, (d - b) * 88.8)      # km
            add_point(e, (a + c) / 2, (b + d) / 2, k * L / 0.2)    # 셀 폭(0.2km) 단위

    def area(self, a):
        t = a.tags
        self.n += 1
        if self.n % 500000 == 0:
            print('  areas', self.n, flush=True)
        b = t.get('building')
        if b and b != 'no':
            try:
                ring = next(iter(a.outer_rings()))
                la = [nd.lat for nd in ring]; lo = [nd.lon for nd in ring]
            except Exception:
                return
            lat, lon = sum(la) / len(la), sum(lo) / len(lo)
            try: lv = float(t.get('building:levels', '0').split(';')[0])
            except ValueError: lv = 0
            add_point(3, lat, lon, 0.3 + min(lv, 40) * 0.12)
            e = poi_weight(t)
            if e is not None:
                add_point(e, lat, lon, 1.0)
            return
        e = area_class(t)
        pw = poi_weight(t)
        if e is None and pw is None:
            return
        try:
            g = swkb.loads(self.wkb.create_multipolygon(a), hex=True)
        except Exception:
            return
        if pw is not None and e is None:
            c = g.representative_point(); add_point(pw, c.y, c.x, 1.0); return
        minx, miny, maxx, maxy = g.bounds
        r0, r1 = int((miny - LAT0) / DLAT), int((maxy - LAT0) / DLAT)
        c0, c1 = int((minx - LON0) / DLON), int((maxx - LON0) / DLON)
        r0, c0 = max(r0, 0), max(c0, 0); r1, c1 = min(r1, ROWS - 1), min(c1, COLS - 1)
        if r1 < r0 or c1 < c0:
            return
        if (r1 - r0 + 1) * (c1 - c0 + 1) <= 2:
            # 셀보다 작은 면: 면적 비율만큼 한 칸에
            frac = g.area / (DLAT * DLON)
            c = g.representative_point(); add_point(e, c.y, c.x, min(1.0, frac))
            return
        rr, cc = np.mgrid[r0:r1 + 1, c0:c1 + 1]
        ys = LAT0 + (rr + 0.5) * DLAT; xs = LON0 + (cc + 0.5) * DLON
        inside = shapely.contains_xy(g, xs.ravel(), ys.ravel()).reshape(rr.shape)
        if inside.any():
            raw[e, rr[inside], cc[inside]] += 1.0
        else:
            c = g.representative_point(); add_point(e, c.y, c.x, min(1.0, g.area / (DLAT * DLON)))


BASE32 = '0123456789bcdefghjkmnpqrstuvwxyz'


def geohash(lat, lon, prec=6):
    la, lo = [-90.0, 90.0], [-180.0, 180.0]
    out, bit, ch, even = [], 0, 0, True
    while len(out) < prec:
        if even:
            m = (lo[0] + lo[1]) / 2
            if lon >= m: ch |= 1 << (4 - bit); lo[0] = m
            else: lo[1] = m
        else:
            m = (la[0] + la[1]) / 2
            if lat >= m: ch |= 1 << (4 - bit); la[0] = m
            else: la[1] = m
        even = not even
        if bit < 4: bit += 1
        else: out.append(BASE32[ch]); bit, ch = 0, 0
    return ''.join(out)


def main(src, dst):
    t0 = time.time()
    print(f'grid {ROWS}×{COLS}', flush=True)
    H().apply_file(src, locations=True, idx='flex_mem')
    print(f'read done {time.time() - t0:.0f}s', flush=True)

    # 반경 500m 버퍼 (셀 200m → 반경 2.5칸 원판)
    rad = 2.5
    k = np.zeros((7, 7), dtype=np.float32)
    for i in range(7):
        for j in range(7):
            if math.hypot(i - 3, j - 3) <= rad: k[i, j] = 1
    buf = np.stack([convolve(raw[e], k, mode='constant') for e in range(5)])

    # 오행마다 단위가 달라서, 수도권 도심에서 값이 있는 셀의 90번째 백분위로 나눠 맞춤
    sr = slice(int((37.4 - LAT0) / DLAT), int((37.7 - LAT0) / DLAT)); sc = slice(int((126.8 - LON0) / DLON), int((127.2 - LON0) / DLON))
    ref = []
    for e in range(5):
        v = buf[e, sr, sc]; v = v[v > 0]
        ref.append(float(np.percentile(v, 90)) if v.size else 1.0)
    ref[4] *= 0.5   # 물은 풍수에서 비중이 커서 절반 양으로도 가득 찬 것으로
    print('ref', dict(zip(EL, [round(x, 2) for x in ref])), flush=True)
    norm = np.stack([np.minimum(buf[e] / ref[e], 3.0) for e in range(5)])

    # geohash6 셀 중심에서 표본
    GLAT, GLON = 180 / 2 ** 15, 360 / 2 ** 15
    recs = {}
    la = math.floor(LAT0 / GLAT) * GLAT
    while la < LAT1:
        lo = math.floor(LON0 / GLON) * GLON
        while lo < LON1:
            clat, clon = la + GLAT / 2, lo + GLON / 2
            rc = cell(clat, clon)
            if rc:
                v = norm[:, rc[0], rc[1]]
                if v.sum() > 0.05:
                    p = (v + 0.05) / (v + 0.05).sum()
                    q = np.floor(p * 255).astype(int)
                    q[int(np.argmax(p))] += 255 - q.sum()
                    flags = (1 if v[4] > 0.5 else 0) | (2 if v[0] > 0.5 else 0)
                    recs[geohash(clat, clon)] = (q.tolist(), flags)
            lo += GLON
        la += GLAT
    keys = sorted(recs)
    with open(dst, 'wb') as f:
        f.write(b'UNGR' + struct.pack('<HI4f', 1, len(keys), LAT0, LON0, LAT1, LON1))
        for g in keys:
            q, fl = recs[g]
            f.write(g.encode('ascii') + bytes(q) + bytes([fl]))
    data = open(dst, 'rb').read()
    man = {'version': 1, 'cells': len(keys), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
           'source': src.split('/')[-1], 'built': time.strftime('%Y-%m-%d'), 'license': 'ODbL © OpenStreetMap contributors'}
    json.dump(man, open(dst.replace('.bin', '.json'), 'w'), ensure_ascii=False, indent=1)
    print(man, f'{time.time() - t0:.0f}s')
    np.save(dst.replace('.bin', '-norm.npy'), norm)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

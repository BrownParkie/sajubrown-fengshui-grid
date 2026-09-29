# 사주박사브라운 풍수 격자 (Korea Five-Element Grid)

대한민국 전역을 geohash 6자리(약 1.2km × 0.6km) 셀로 나누고, 셀마다 주변 500m의 환경을
**오행(목·화·토·금·수) 분포**로 요약한 데이터베이스입니다.
iOS 앱 **사주박사브라운**의 ‘행운 번호 › 지금 여기’ 기능이 기기 안에서 이 파일을 조회합니다.

This database summarizes the surroundings (500 m buffer) of every geohash-6 cell in South Korea
as a five-element (wood · fire · earth · metal · water) distribution. It is used offline by the iOS app *SajuBrown*.

## 출처와 라이선스 · Source and license

- 원본 데이터: © **OpenStreetMap contributors** — https://www.openstreetmap.org/copyright
- 이 데이터베이스(`grid-v1.bin`)는 OpenStreetMap에서 파생된 데이터베이스이며
  **Open Database License (ODbL) 1.0** 으로 공개합니다 — https://opendatacommons.org/licenses/odbl/1-0/
- This database is a derivative of OpenStreetMap data and is made available under the ODbL 1.0.
  Individual contents are under the Database Contents License (DbCL) 1.0.
- 생성 스크립트(`build_grid.py`, `check_grid.py`)는 재현을 위해 함께 공개합니다.

## 만든 방법

- 입력: Geofabrik `south-korea-latest.osm.pbf` (`grid-v1.json`의 `built` 날짜 기준)
- 약 200m 래스터에 오행 원재료를 쌓은 뒤 반경 500m로 흐리게 하고, geohash6 셀 중심에서 표본을 뽑습니다.

| 오행 | 근거 (OSM 태그) |
|---|---|
| 목 | 공원·숲·풀밭·과수원·가로수 (`leisure=park`, `landuse=forest/grass/meadow/orchard`, `natural=wood/scrub`, `natural=tree_row`) |
| 화 | 상점·음식점·카페·상업지 (`shop=*`, `amenity=restaurant/cafe/bar…`, `landuse=retail/commercial`) |
| 토 | 농지·운동장·광장·주차장·학교 (`landuse=farmland…`, `leisure=pitch/stadium`, `place=square`, `amenity=parking/school`) |
| 금 | 건물(층수 가중)·산업지·바위·관공서 (`building=*`, `landuse=industrial`, `natural=bare_rock`, `amenity=bank/hospital…`) |
| 수 | 하천·호수·저수지·습지·해안선·분수 (`waterway=*`, `natural=water/wetland/coastline`, `landuse=reservoir`, `amenity=fountain`) |

## 파일 형식 `grid-v1.bin`

```
헤더 26바이트
  magic      'UNGR'            4 bytes
  version    uint16 LE         2
  cellCount  uint32 LE         4
  bbox       float32 LE × 4    16  (minLat, minLon, maxLat, maxLon)
레코드 × cellCount, geohash 오름차순, 레코드당 12바이트
  geohash    ASCII 6 bytes
  P[5]       uint8 × 5         목 화 토 금 수 (합 255)
  flags      uint8             bit0 물 가까움, bit1 녹지 가까움
```

셀이 없으면(바다 한가운데 등) 앱은 중립 분포 `[0.2, 0.2, 0.2, 0.2, 0.2]`를 씁니다.
무결성: `grid-v1.json`의 `sha256`.

## 다시 만들기

```bash
pip install osmium shapely numpy scipy
curl -LO https://download.geofabrik.de/asia/south-korea-latest.osm.pbf
python build_grid.py south-korea-latest.osm.pbf grid-v1.bin
python check_grid.py grid-v1.bin
```

문의: admin@supercarrot.net · © Super Carrot

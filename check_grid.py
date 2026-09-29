"""격자 파일 눈 검증 (04 1.4 S6): 성격이 다른 고정 지점들의 오행 분포를 출력합니다.
사용: python check_grid.py grid-v1.bin
"""
import sys, struct, bisect
from build_grid import geohash

SPOTS = [
    ('강남역 (상업)', 37.4979, 127.0276),
    ('명동 (상업)', 37.5636, 126.9826),
    ('청계천 (물길·도심)', 37.5696, 126.9784),
    ('여의도한강공원 (강)', 37.5284, 126.9336),
    ('올림픽공원 (공원)', 37.5206, 127.1214),
    ('북한산 (산)', 37.6587, 126.9780),
    ('잠실 아파트 단지 (주거)', 37.5115, 127.0850),
    ('구로디지털단지 (고층·산업)', 37.4850, 126.8960),
    ('김포 들녘 (농지)', 37.6900, 126.6300),
    ('해운대 (바다)', 35.1587, 129.1604),
    ('제주 시내', 33.4996, 126.5312),
]
EL = '목화토금수'


def load(path):
    d = open(path, 'rb').read()
    assert d[:4] == b'UNGR'
    ver, n = struct.unpack('<HI', d[4:10])
    keys, vals = [], []
    for i in range(n):
        o = 26 + i * 12
        keys.append(d[o:o + 6].decode()); vals.append((list(d[o + 6:o + 11]), d[o + 11]))
    return keys, vals


if __name__ == '__main__':
    keys, vals = load(sys.argv[1])
    print(f'{len(keys)} cells')
    for name, lat, lon in SPOTS:
        g = geohash(lat, lon)
        i = bisect.bisect_left(keys, g)
        if i < len(keys) and keys[i] == g:
            q, fl = vals[i]
            top = max(range(5), key=lambda e: q[e])
            print(f'{name:22s} {g}  ' + '  '.join(f'{EL[e]} {q[e] / 255:.2f}' for e in range(5)) + f'   → {EL[top]}  flags {fl}')
        else:
            print(f'{name:22s} {g}  (셀 없음 → 중립)')

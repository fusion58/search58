"""
Search58 — benchmark de throughput
Uso: python benchmark.py [--url URL] [--n N] [--workers W]

Envía N peticiones /reverse con puntos aleatorios de Venezuela,
W en paralelo (threads), y reporta req/s, latencias p50/p95/p99.
"""
import argparse
import random
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import json

LAT_MIN, LAT_MAX = 0.65, 12.20
LON_MIN, LON_MAX = -73.35, -59.80

def random_ve():
    return (
        random.uniform(LAT_MIN, LAT_MAX),
        random.uniform(LON_MIN, LON_MAX),
    )

def fetch_real_points(url_base, n):
    """Obtiene N puntos reales de referencepoints via /sample-points."""
    url = f'{url_base}/sample-points?n={n}'
    with urllib.request.urlopen(url, timeout=15) as r:
        pts = json.loads(r.read())
    return [(p['lat'], p['lon']) for p in pts]

def call_reverse(url_base, lat, lon):
    url = f'{url_base}/reverse?lat={lat:.6f}&lon={lon:.6f}'
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        ms = (time.monotonic() - t0) * 1000
        return ms, data.get('source', '?'), None
    except Exception as e:
        ms = (time.monotonic() - t0) * 1000
        return ms, 'error', str(e)

def run(url, n, workers):
    print('Cargando puntos reales desde /sample-points...')
    try:
        pts = fetch_real_points(url, n)
        print(f'{len(pts)} puntos cargados de referencepoints (Venezuela)\n')
    except Exception:
        pts = [random_ve() for _ in range(n)]
        print(f'(fallback: puntos aleatorios)\n')
    results = []
    errors = 0
    sources = {'f58': 0, 'nominatim': 0, 'error': 0, 'sininfo': 0}

    print(f'\nSearch58 benchmark — {n} puntos, {workers} workers paralelos')
    print(f'URL: {url}/reverse\n')

    t_start = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(call_reverse, url, lat, lon): i
                   for i, (lat, lon) in enumerate(pts)}
        done = 0
        for fut in as_completed(futures):
            ms, src, err = fut.result()
            results.append(ms)
            sources[src if src in sources else 'error'] += 1
            if err:
                errors += 1
            done += 1
            if done % 50 == 0 or done == n:
                elapsed = time.monotonic() - t_start
                print(f'  {done}/{n}  {elapsed:.1f}s  {done/elapsed:.1f} req/s', end='\r')

    elapsed = time.monotonic() - t_start
    results.sort()

    def pct(p): return results[int(len(results) * p / 100)]

    print(f'\n{"-"*50}')
    print(f'Total:      {n} peticiones en {elapsed:.2f}s')
    print(f'Throughput: {n/elapsed:.1f} req/s')
    print(f'Latencia:')
    print(f'  p50  {pct(50):.0f} ms')
    print(f'  p95  {pct(95):.0f} ms')
    print(f'  p99  {pct(99):.0f} ms')
    print(f'  max  {max(results):.0f} ms')
    print(f'  avg  {statistics.mean(results):.0f} ms')
    print(f'Fuentes:    F58={sources["f58"]}  Nominatim={sources["nominatim"]}  Sin info={sources["sininfo"]}  Error={sources["error"]}')
    print('-'*50)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--url',     default='http://100.75.222.2:7171')
    p.add_argument('--n',       type=int, default=200)
    p.add_argument('--workers', type=int, default=10)
    args = p.parse_args()
    run(args.url, args.n, args.workers)

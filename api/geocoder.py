import os
import httpx
from db import run_sql

NOMINATIM_URL     = os.environ.get('NOMINATIM_URL',     'https://nominatim.openstreetmap.org')
NOMINATIM_TIMEOUT = int(os.environ.get('NOMINATIM_TIMEOUT', '5'))
HYBRID_THRESHOLD  = int(os.environ.get('HYBRID_THRESHOLD',  '13'))


def score_address(addr: dict) -> int:
    if not addr:
        return 0
    s = 0
    if addr.get('road'):                                 s += 10
    if addr.get('neighbourhood') or addr.get('suburb'):  s += 5
    if addr.get('city'):                                 s += 3
    if addr.get('county'):                               s += 2
    if addr.get('state'):                                s += 2
    if addr.get('country'):                              s += 1
    return s


def geocode_f58(lat: float, lon: float) -> dict:
    sql = (
        "SELECT fulladdress, shortaddress, "
        "nameurbanroads, nametownroads, nameorder9area, nameorder8area, "
        "nameorder2area, denominationorder2area, "
        "nameorder1area, denominationorder1area, namecountry "
        "FROM buscador.f_geocodificacion_inversa("
        "ST_SetSRID(ST_MakePoint(%s, %s), 4326));"
    )
    rows = run_sql(sql, (lon, lat))
    if not rows or not rows[0][0]:
        return {'display_name': 'Sin información', 'address': {}}

    (fulladdress, shortaddress,
     nameurbanroads, nametownroads,
     nameorder9area, nameorder8area,
     nameorder2area, denomorder2,
     nameorder1area, denomorder1,
     namecountry) = rows[0]

    road   = nameurbanroads or nametownroads or ''
    suburb = nameorder9area or ''
    city   = nameorder8area or ''
    county = (f'{denomorder2} {nameorder2area}'.strip()) if nameorder2area else ''
    state  = (f'{denomorder1} {nameorder1area}'.strip()) if nameorder1area else ''

    country_lower = (namecountry or '').lower()
    if 'venezuel'  in country_lower: cc = 've'
    elif 'méxico'  in country_lower or 'mexico' in country_lower: cc = 'mx'
    elif 'guatemal' in country_lower: cc = 'gt'
    else: cc = ''

    return {
        'display_name': fulladdress or shortaddress or 'Sin información',
        'lat': str(lat),
        'lon': str(lon),
        'source': 'f58',
        'address': {
            'road':          road,
            'neighbourhood': suburb,
            'city':          city,
            'county':        county,
            'state':         state,
            'country':       namecountry or '',
            'country_code':  cc,
        },
    }


def geocode_nominatim(lat: float, lon: float) -> dict | None:
    url = (f'{NOMINATIM_URL}/reverse'
           f'?format=json&lat={lat}&lon={lon}&addressdetails=1&accept-language=es')
    try:
        with httpx.Client(timeout=NOMINATIM_TIMEOUT,
                          headers={'User-Agent': 'Search58/1.0 (geocoding proxy)'}) as client:
            resp = client.get(url)
            data = resp.json()
    except Exception:
        return None

    a = data.get('address', {})
    return {
        'display_name': data.get('display_name', ''),
        'lat': data.get('lat', str(lat)),
        'lon': data.get('lon', str(lon)),
        'source': 'nominatim',
        'address': {
            'road':          a.get('road') or a.get('pedestrian') or a.get('footway') or '',
            'neighbourhood': a.get('suburb') or a.get('neighbourhood') or a.get('quarter') or '',
            'city':          a.get('city') or a.get('town') or a.get('village') or '',
            'county':        a.get('county') or '',
            'state':         a.get('state') or '',
            'country':       a.get('country') or '',
            'country_code':  a.get('country_code') or '',
        },
    }


def geocode_hybrid(lat: float, lon: float) -> dict:
    f58 = geocode_f58(lat, lon)
    f58_score = score_address(f58.get('address', {}))
    f58['score'] = f58_score

    if f58_score >= HYBRID_THRESHOLD:
        return f58

    nom = geocode_nominatim(lat, lon)
    if nom:
        nom_score = score_address(nom.get('address', {}))
        nom['score']     = nom_score
        nom['f58_score'] = f58_score
        if nom_score > f58_score:
            return nom

    return f58


def search_places(q: str, limit: int = 10) -> list:
    sql = (
        "SELECT nombre, ubicacion, tipo, px, py, "
        "x_min, y_min, x_max, y_max "
        "FROM buscador.f_search_in_country(%s, 862, %s);"
    )
    rows = run_sql(sql, (q, limit))
    results = []
    for row in rows:
        nombre, ubicacion, tipo, px, py, x_min, y_min, x_max, y_max = row
        if px is None or py is None:
            continue
        results.append({
            'display_name': ubicacion or nombre,
            'name':         nombre,
            'lat':          str(py),
            'lon':          str(px),
            'boundingbox':  [str(y_min), str(y_max), str(x_min), str(x_max)],
            'type':         tipo or 'place',
            'class':        'place',
            'source':       'f58',
        })
    return results

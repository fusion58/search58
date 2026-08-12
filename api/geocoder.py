import os
import urllib.parse
import httpx
from db import run_sql

NOMINATIM_URL     = os.environ.get('NOMINATIM_URL',     'https://nominatim.openstreetmap.org')
NOMINATIM_TIMEOUT = int(os.environ.get('NOMINATIM_TIMEOUT', '5'))
HYBRID_THRESHOLD  = int(os.environ.get('HYBRID_THRESHOLD',  '13'))

# Mapeo GeoNames feature_code → tipo en español (para display_name normalizado)
_GEONAMES_TYPE = {
    # H — Hidrografía
    'STM': 'Río', 'STMI': 'Río', 'STMQ': 'Río', 'STMSB': 'Río',
    'LK': 'Lago', 'LKI': 'Lago', 'LKN': 'Lago',
    'RSV': 'Embalse', 'RSVH': 'Embalse',
    'BAY': 'Bahía', 'BAYS': 'Bahía',
    'GULF': 'Golfo', 'COVE': 'Ensenada',
    'CHAN': 'Canal', 'SD': 'Caño',
    'FALL': 'Cascada', 'FALLS': 'Cascada',
    'SWMP': 'Pantano', 'MRSH': 'Marisma',
    'CAPE': 'Cabo', 'PEN': 'Península',
    'LAGN': 'Laguna', 'LGNX': 'Laguna',
    # T — Relieve
    'MT': 'Cerro', 'MTS': 'Serranía', 'PK': 'Pico',
    'HLL': 'Colina', 'HLLS': 'Colinas',
    'ISL': 'Isla', 'ISLS': 'Islas', 'ISLET': 'Islote',
    'PT': 'Punta', 'HDLD': 'Cabo',
    'VLC': 'Volcán', 'MESA': 'Mesa', 'PLN': 'Llano',
    'VAL': 'Valle', 'RDGE': 'Serranía',
    # L — Áreas
    'PRK': 'Parque Nacional', 'PRKX': 'Parque',
    'RESV': 'Reserva', 'RESW': 'Reserva',
    'AREA': 'Área', 'RGN': 'Región',
    'LCTY': 'Localidad', 'CONT': 'Área',
    # P — Poblados
    'PPL': 'Población', 'PPLL': 'Población', 'PPLX': 'Sector',
    'PPLA': 'Capital de Estado', 'PPLA2': 'Capital de Municipio',
    'PPLA3': 'Capital de Parroquia', 'PPLC': 'Capital',
    # V — Vegetación
    'FRST': 'Bosque', 'GRSLD': 'Sabana',
}


def score_address(addr: dict) -> int:
    if not addr:
        return 0
    s = 0
    if addr.get('road'):                                 s += 10
    if addr.get('neighbourhood') or addr.get('suburb'):  s += 5
    # No contar city si F58 puso una Parroquia en ese campo (dato incorrecto)
    city = addr.get('city', '')
    if city and 'parroquia' not in city.lower():         s += 3
    if addr.get('county'):                               s += 2
    if addr.get('state'):                                s += 2
    if addr.get('country'):                              s += 1
    # Código postal: Nominatim lo incluye, F58 no → ventaja real de información
    if addr.get('postcode'):                             s += 2
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
            'postcode':      a.get('postcode') or '',
        },
    }


def _get_tiletype(lat: float, lon: float) -> int | None:
    """Retorna tiletype del tile que contiene el punto.
    tiletype=1 → tierra firme (flujo híbrido normal)
    tiletype=0 → agua/costa/zona insular (F58 es autoritativo, no llamar Nominatim)
    None       → fuera de todos los tiles
    """
    sql = (
        "SELECT tiletype FROM buscador.country_tiles "
        "WHERE the_geom && ST_SetSRID(ST_MakePoint(%s, %s), 4326) "
        "AND ST_Contains(the_geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) "
        "LIMIT 1"
    )
    rows = run_sql(sql, (lon, lat, lon, lat))
    return rows[0][0] if rows else None


def geocode_hybrid(lat: float, lon: float) -> dict:
    f58 = geocode_f58(lat, lon)
    f58_score = score_address(f58.get('address', {}))
    f58['score'] = f58_score

    if f58_score >= HYBRID_THRESHOLD:
        return f58

    # Para zonas marítimas/costeras (tiletype=0), F58 es la fuente autoritativa.
    # country_tiles ya tiene la información correcta (Mar Caribe, Zona Costera, etc.)
    # Nominatim no tiene información útil para esas coordenadas.
    if f58.get('display_name', 'Sin información') != 'Sin información':
        tiletype = _get_tiletype(lat, lon)
        if tiletype == 0:
            return f58

    nom = geocode_nominatim(lat, lon)
    if nom:
        nom_score = score_address(nom.get('address', {}))
        nom['score']     = nom_score
        nom['f58_score'] = f58_score
        if nom_score > f58_score:
            return nom

    return f58


def sample_points(n: int) -> list:
    n = max(1, min(n, 500))
    sql = (
        "SELECT ROUND(ST_Y(the_geom)::numeric, 7)::float, "
        "       ROUND(ST_X(the_geom)::numeric, 7)::float "
        "FROM buscador.referencepoints "
        "WHERE codecountry = 862 AND the_geom IS NOT NULL "
        "ORDER BY RANDOM() LIMIT %s;"
    )
    rows = run_sql(sql, (n,))
    return [{'lat': row[0], 'lon': row[1]} for row in rows]


_STOPWORDS = {
    'las', 'los', 'la', 'el', 'de', 'del', 'y', 'a', 'en',
    'con', 'por', 'para', 'que', 'se', 'al', 'un', 'una',
}

# Palabras que indican que el query busca geografía natural → GeoNames primero
_GEO_INDICATORS = {
    'rio', 'rios', 'cerro', 'cerros', 'pico', 'picos',
    'lago', 'lagos', 'laguna', 'lagunas', 'embalse', 'represa',
    'isla', 'islas', 'islote', 'montana', 'montanas', 'serranía', 'sierra',
    'parque', 'reserva', 'cordillera', 'tepuy', 'tepui',
    'golfo', 'bahia', 'cabo', 'cascada', 'salto', 'catarata',
    'caño', 'cano', 'quebrada', 'delta', 'peninsula',
    'nacional', 'natural',
}

def _geo_score(query_words: set, ubicacion: str) -> float:
    """Fracción de palabras significativas del query que aparecen en la ubicacion.
    Usa match por prefijo (stem simple) para cubrir singular/plural:
    'residencias' matchea 'residencia', 'caracas' matchea 'caracas', etc.
    """
    if not ubicacion or not query_words:
        return 0.0
    ub = ubicacion.lower()
    matches = 0
    for w in query_words:
        # Stem: quitar hasta 2 chars del final para cubrir variaciones morfológicas
        stem = w[:max(5, len(w) - 1)]
        if stem in ub:
            matches += 1
    return matches / len(query_words)

def _significant_words(q: str) -> set:
    """Palabras del query que no son stopwords y tienen 3+ caracteres."""
    return {w for w in q.lower().split() if w not in _STOPWORDS and len(w) >= 3}


def search_places(q: str, limit: int = 10) -> list:
    # Pedimos más candidatos para poder re-rankear geográficamente
    # Si el query contiene indicadores de geografía natural → GeoNames primero
    q_lower_words = set(q.lower().split())
    if q_lower_words & _GEO_INDICATORS:
        geo_results = _search_geonames(q, limit)
        if geo_results:
            return geo_results

    fetch = max(limit * 5, 50)
    sql = (
        "SELECT nombre, ubicacion, tipo, px, py, "
        "x_min, y_min, x_max, y_max "
        "FROM buscador.f_search_in_country(%s, 862, %s);"
    )
    rows = run_sql(sql, (q, fetch))
    sig_words = _significant_words(q)
    results = []
    for row in rows:
        nombre, ubicacion, tipo, px, py, x_min, y_min, x_max, y_max = row
        if px is None or py is None:
            continue
        geo = _geo_score(sig_words, ubicacion)
        results.append({
            'display_name': ubicacion or nombre,
            'name':         nombre,
            'lat':          str(py),
            'lon':          str(px),
            'boundingbox':  [str(y_min), str(y_max), str(x_min), str(x_max)],
            'type':         tipo or 'place',
            'class':        'place',
            'source':       'f58',
            '_geo':         geo,
        })

    # Re-rankear por coincidencia geográfica y retornar top N
    results.sort(key=lambda r: r['_geo'], reverse=True)
    for r in results:
        del r['_geo']

    if results:
        return results[:limit]

    # F58 sin resultados → intentar GeoNames (geografía natural)
    geo_results = _search_geonames(q, limit)
    if geo_results:
        return geo_results

    # Nada en GeoNames → fallback final a Nominatim
    return _search_nominatim(q, limit)


def _search_geonames(q: str, limit: int) -> list:
    """Busca en buscador.geonames usando similitud trigram sobre name y asciiname."""
    sql = (
        "SELECT geonameid, name, feature_class, feature_code, "
        "latitude, longitude "
        "FROM buscador.geonames "
        "WHERE name %%>> %s OR asciiname %%>> %s "
        "ORDER BY GREATEST(word_similarity(%s, name), word_similarity(%s, asciiname)) DESC "
        "LIMIT %s;"
    )
    try:
        rows = run_sql(sql, (q, q, q, q, limit))
    except Exception:
        return []

    results = []
    for row in rows:
        gid, name, fc, code, lat, lon = row
        tipo = _GEONAMES_TYPE.get(code, _GEONAMES_TYPE.get(fc, 'Lugar'))
        display = f'{name}. {tipo}. Venezuela.'
        results.append({
            'display_name': display,
            'name':         name,
            'lat':          str(lat),
            'lon':          str(lon),
            'boundingbox':  [str(lat), str(lat), str(lon), str(lon)],
            'type':         tipo,
            'class':        'place',
            'source':       'geonames',
        })
    return results


def _search_nominatim(q: str, limit: int) -> list:
    """Fallback a Nominatim cuando F58 no devuelve resultados."""
    url = (f'{NOMINATIM_URL}/search'
           f'?format=json&q={urllib.parse.quote(q)}'
           f'&limit={limit}&addressdetails=1&accept-language=es')
    try:
        with httpx.Client(timeout=NOMINATIM_TIMEOUT,
                          headers={'User-Agent': 'Search58/1.0 (geocoding proxy)'}) as client:
            resp = client.get(url)
            data = resp.json()
    except Exception:
        return []

    results = []
    for item in data:
        lat = item.get('lat', '')
        lon = item.get('lon', '')
        if not lat or not lon:
            continue
        bb = item.get('boundingbox', [lat, lat, lon, lon])
        raw = item.get('display_name', '')
        # Normalizar separadores: comas → puntos, igual que F58
        display = raw.replace(', ', '. ')
        name = raw.split(',')[0].strip()
        results.append({
            'display_name': display,
            'name':         name,
            'lat':          lat,
            'lon':          lon,
            'boundingbox':  bb,
            'type':         item.get('type') or item.get('class') or 'place',
            'class':        item.get('class') or 'place',
            'source':       'nominatim',
        })
    return results

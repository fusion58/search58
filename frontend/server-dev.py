"""
Search58 — servidor de desarrollo local

Sirve tres cosas desde el mismo puerto (7070):
  - Archivos estáticos desde el directorio donde vive este script
      http://localhost:7171/geocode-compare.html
  - API de geocodificación inversa (compatible Nominatim)
      http://localhost:7171/reverse?format=json&lat=<lat>&lon=<lon>
  - Proxy de GeoServer para el mapa F58 (tiles MVT)
      http://localhost:7171/geoserver/... → localhost:8080/geoserver/...
      (override con variable GEOSERVER_URL)

Llama a f_geocodificacion_inversa() en la BD local (localhost:5433/buscador).

Uso:
  set PGPASSWORD=<clave>   (Windows)
  python server-dev.py
"""
import http.server
import urllib.parse
import urllib.request
import json
import subprocess
import os
import sys

PORT     = 7171
PG_HOST  = 'localhost'
PG_PORT  = '5433'
PG_USER  = 'postgres'
PG_DB    = 'buscador'

GEOSERVER_UPSTREAM  = os.environ.get('GEOSERVER_URL',  'http://localhost:8080')
NOMINATIM_URL       = os.environ.get('NOMINATIM_URL',  'https://nominatim.openstreetmap.org')
NOMINATIM_TIMEOUT   = int(os.environ.get('NOMINATIM_TIMEOUT', '5'))
HYBRID_THRESHOLD    = 13   # score F58 mínimo para retornar sin llamar a Nominatim

def score_address(addr):
    """Puntaje de completitud (max 23). Determina qué fuente gana en modo híbrido."""
    if not addr:
        return 0
    s = 0
    if addr.get('road'):                            s += 10
    if addr.get('neighbourhood') or addr.get('suburb'): s += 5
    if addr.get('city'):                            s += 3
    if addr.get('county'):                          s += 2
    if addr.get('state'):                           s += 2
    if addr.get('country'):                         s += 1
    return s

def geocode_nominatim(lat, lon):
    url = ('{}/reverse?format=json&lat={}&lon={}&addressdetails=1'
           '&accept-language=es').format(NOMINATIM_URL, lat, lon)
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Search58-Dev/1.0 (geocoding validation)'
        })
        with urllib.request.urlopen(req, timeout=NOMINATIM_TIMEOUT) as resp:
            data = json.loads(resp.read().decode('utf-8'))
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
                'country_code':  a.get('country_code') or ''
            }
        }
    except Exception:
        return None

def run_sql(sql):
    env = dict(os.environ)
    result = subprocess.run(
        ['psql', '-h', PG_HOST, '-p', PG_PORT, '-U', PG_USER, '-d', PG_DB,
         '-t', '-A', '-c', sql],
        capture_output=True, text=True, encoding='utf-8', env=env
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()

def geocode_inverse(lat, lon):
    """
    Llama a f_geocodificacion_inversa y devuelve un dict compatible con
    el formato de respuesta de Nominatim (display_name + address).
    """
    sql = (
        "SELECT fulladdress, shortaddress, "
        "nameurbanroads, nametownroads, nameorder9area, nameorder8area, "
        "nameorder2area, denominationorder2area, "
        "nameorder1area, denominationorder1area, namecountry "
        "FROM buscador.f_geocodificacion_inversa("
        "ST_SetSRID(ST_MakePoint({lon},{lat}),4326));"
    ).format(lat=float(lat), lon=float(lon))

    raw = run_sql(sql)
    if not raw:
        return {"display_name": "Sin información", "address": {}}

    cols = raw.split('|')
    if len(cols) < 11:
        return {"display_name": raw, "address": {}}

    fulladdress, shortaddress    = cols[0], cols[1]
    nameurbanroads, nametownroads = cols[2], cols[3]
    nameorder9area, nameorder8area = cols[4], cols[5]
    nameorder2area, denomorder2   = cols[6], cols[7]
    nameorder1area, denomorder1   = cols[8], cols[9]
    namecountry                   = cols[10]

    road   = nameurbanroads or nametownroads or ''
    suburb = nameorder9area or ''
    city   = nameorder8area or ''
    county = (denomorder2 + ' ' + nameorder2area).strip() if nameorder2area else ''
    state  = (denomorder1 + ' ' + nameorder1area).strip() if nameorder1area else ''

    # country_code: mapa interno → ISO 3166-1 alpha-2
    CC_MAP = {862: 've', 484: 'mx', 320: 'gt'}
    country_code = CC_MAP.get(int(cols[0].split('|')[0]) if False else 862, '')
    # codecountry no está en esta query; derivamos de namecountry como fallback
    country_lower = (namecountry or '').lower()
    if 'venezuel' in country_lower:   country_code = 've'
    elif 'méxico' in country_lower or 'mexico' in country_lower: country_code = 'mx'
    elif 'guatemala' in country_lower: country_code = 'gt'
    else: country_code = ''

    return {
        "display_name": fulladdress or shortaddress or "Sin información",
        "lat": str(lat),
        "lon": str(lon),
        "source": "f58",
        "address": {
            "road":         road,
            "neighbourhood": suburb,
            "city":         city,
            "county":       county,
            "state":        state,
            "country":      namecountry or '',
            "country_code": country_code
        }
    }


def geocode_hybrid(lat, lon):
    """Lógica híbrida: F58 primero; si es suficiente, retorna sin llamar a Nominatim."""
    f58 = geocode_inverse(lat, lon)
    f58['source'] = 'f58'
    f58_score = score_address(f58.get('address', {}))
    f58['score'] = f58_score

    if f58_score >= HYBRID_THRESHOLD:
        return f58

    # F58 incompleto → intentar Nominatim como fallback
    nom = geocode_nominatim(lat, lon)
    if nom:
        nom_score = score_address(nom.get('address', {}))
        nom['score'] = nom_score
        nom['f58_score'] = f58_score
        if nom_score > f58_score:
            return nom

    return f58


def sample_reference_points(n):
    """Devuelve N puntos aleatorios de buscador.referencepoints (Venezuela)."""
    n = max(1, min(n, 500))
    sql = (
        "SELECT ROUND(ST_Y(the_geom)::numeric, 7)::text, "
        "       ROUND(ST_X(the_geom)::numeric, 7)::text "
        "FROM buscador.referencepoints "
        "WHERE codecountry = 862 AND the_geom IS NOT NULL "
        "ORDER BY RANDOM() LIMIT {};".format(n)
    )
    raw = run_sql(sql)
    if not raw:
        return []
    points = []
    for line in raw.split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split('|')
        if len(parts) < 2:
            continue
        try:
            points.append({'lat': float(parts[0]), 'lon': float(parts[1])})
        except ValueError:
            continue
    return points


def search_places(q, limit=10):
    sql = (
        "SELECT nombre, ubicacion, tipo, px, py, "
        "x_min, y_min, x_max, y_max "
        "FROM buscador.f_search_in_country('{}', 862, {});".format(
            q.replace("'", "''"), int(limit)
        )
    )
    raw = run_sql(sql)
    if not raw:
        return []
    results = []
    for line in raw.split('\n'):
        line = line.strip()
        if not line:
            continue
        cols = line.split('|')
        if len(cols) < 9:
            continue
        nombre, ubicacion, tipo, px, py = cols[0], cols[1], cols[2], cols[3], cols[4]
        x_min, y_min, x_max, y_max = cols[5], cols[6], cols[7], cols[8]
        if not px or not py:
            continue
        results.append({
            "name":         nombre,
            "display_name": ubicacion or nombre,
            "lat":          py,
            "lon":          px,
            "boundingbox":  [y_min, y_max, x_min, x_max],
            "type":         tipo or "place",
            "class":        "place",
            "source":       "f58"
        })
    return results


# Directorio desde donde se sirven los archivos estáticos (donde vive este script)
STATIC_DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    """Sirve archivos estáticos + endpoint /reverse."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == '/reverse':
            self._handle_reverse()
        elif path == '/search':
            self._handle_search()
        elif path == '/sample-points':
            self._handle_sample_points()
        elif path.startswith('/geoserver/'):
            self._proxy_geoserver()
        else:
            super().do_GET()  # archivo estático normal

    def _handle_reverse(self):
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        try:
            lat = float(params['lat'])
            lon = float(params['lon'])
        except (KeyError, ValueError):
            self._json(400, {'error': 'Se requieren lat y lon numéricos'})
            return
        try:
            data = geocode_hybrid(lat, lon)
            self._json(200, data)
        except Exception as e:
            self._json(500, {'error': str(e)})

    def _handle_sample_points(self):
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        try:
            n = int(params.get('n', '100'))
        except ValueError:
            n = 100
        try:
            points = sample_reference_points(n)
            self._json(200, points)
        except Exception as e:
            self._json(500, {'error': str(e)})

    def _handle_search(self):
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        q = params.get('q', '').strip()
        limit = min(int(params.get('limit', '10')), 50)
        if not q:
            self._json(400, {'error': 'Se requiere el parámetro q'})
            return
        try:
            results = search_places(q, limit)
            self._json(200, results)
        except Exception as e:
            self._json(500, {'error': str(e)})

    def _proxy_geoserver(self):
        target = GEOSERVER_UPSTREAM + self.path
        try:
            req = urllib.request.Request(target, headers={'Host': 'localhost'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read()
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ('transfer-encoding', 'connection'):
                        self.send_header(k, v)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(body)
        except Exception as e:
            self._json(502, {'error': 'GeoServer no disponible: ' + str(e)})

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type',   'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stdout.write('[%s] %s\n' % (self.log_date_time_string(), args[1]))
        sys.stdout.flush()


if __name__ == '__main__':
    if not os.environ.get('PGPASSWORD'):
        print('AVISO: PGPASSWORD no está definido.')
        print('  Windows: set PGPASSWORD=<clave> && python server-dev.py')

    server = http.server.ThreadingHTTPServer(('localhost', PORT), Handler)
    print('Search58 dev-server en http://localhost:%d' % PORT)
    print('  Comparador:  http://localhost:%d/geocode-compare.html' % PORT)
    print('  API:         http://localhost:%d/reverse?lat=10.4806&lon=-66.9036' % PORT)
    print('  (Puerto 7070 lo ocupa AnyDesk — usamos %d)' % PORT)
    print('Ctrl+C para detener.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nDetenido.')

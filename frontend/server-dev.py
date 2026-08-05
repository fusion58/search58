"""
Search58 — servidor de geocodificación inversa (modo desarrollo local)

Expone la misma interfaz que Nominatim:
  GET /reverse?format=json&lat=<lat>&lon=<lon>

Llama a buscador.obtener_direccion() y f_geocodificacion_inversa()
en la BD local (localhost:5433/buscador).

Uso:
  set PGPASSWORD=<clave>
  python server-dev.py

  O directamente:
  PGPASSWORD=<clave> python server-dev.py
"""
import http.server
import urllib.parse
import json
import subprocess
import os
import sys

PORT     = 7070
PG_HOST  = 'localhost'
PG_PORT  = '5433'
PG_USER  = 'postgres'
PG_DB    = 'buscador'

def run_sql(sql):
    env = dict(os.environ)
    result = subprocess.run(
        ['psql', '-h', PG_HOST, '-p', PG_PORT, '-U', PG_USER, '-d', PG_DB,
         '-t', '-A', '-c', sql],
        capture_output=True, text=True, env=env
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

    return {
        "display_name": fulladdress or shortaddress or "Sin información",
        "address": {
            "road":    road,
            "suburb":  suburb,
            "city":    city,
            "county":  county,
            "state":   state,
            "country": namecountry or ''
        }
    }


class Handler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != '/reverse':
            self._respond(404, {'error': 'Not found'})
            return

        params = dict(urllib.parse.parse_qsl(parsed.query))
        try:
            lat = float(params['lat'])
            lon = float(params['lon'])
        except (KeyError, ValueError):
            self._respond(400, {'error': 'Se requieren lat y lon numéricos'})
            return

        try:
            data = geocode_inverse(lat, lon)
            self._respond(200, data)
        except Exception as e:
            self._respond(500, {'error': str(e)})

    def _respond(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type',  'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        lat = lon = '?'
        if 'lat=' in self.path:
            try:
                p = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
                lat, lon = p.get('lat','?'), p.get('lon','?')
            except Exception:
                pass
        sys.stdout.write('[%s] %s -> lat=%s lon=%s\n' % (
            self.log_date_time_string(), args[1], lat, lon))
        sys.stdout.flush()


if __name__ == '__main__':
    if not os.environ.get('PGPASSWORD'):
        print('AVISO: PGPASSWORD no está definido. Establécelo antes de iniciar.')
        print('  Windows: set PGPASSWORD=<clave> && python server-dev.py')
        print('  Linux:   PGPASSWORD=<clave> python server-dev.py')

    server = http.server.HTTPServer(('localhost', PORT), Handler)
    print('Search58 dev-server escuchando en http://localhost:%d/reverse' % PORT)
    print('Abre: frontend/geocode-compare.html (sirve con Live Server o similar)')
    print('Ctrl+C para detener.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nDetenido.')

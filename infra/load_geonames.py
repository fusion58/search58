"""Carga datos de GeoNames Venezuela en buscador.geonames"""
import subprocess, os, tempfile, sys
env = dict(os.environ); env['PGPASSWORD'] = 'casa1234'
HOST = os.environ.get('PG_HOST', 'localhost')
PORT = os.environ.get('PG_PORT', '5433')

KEEP_CLASSES = {'H', 'T', 'L', 'V'}
KEEP_PCODES  = {'PPL','PPLA','PPLA2','PPLA3','PPLC','PPLX','PPLL'}
EXCL_CODES   = {'FRM','EST','TRIG','RDGE','MTS'}

src = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\apacheco\AppData\Local\Temp\geonames_ve\VE.txt'

# Filtrar y escribir TSV temporal
tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False, encoding='utf-8', newline='')
count = 0
with open(src, encoding='utf-8') as f:
    for line in f:
        p = line.rstrip('\n').split('\t')
        if len(p) < 19:
            continue
        gid, name, ascii_n = p[0], p[1], p[2]
        lat, lon, fc, code = p[4], p[5], p[6], p[7]
        pop, elev, tz = p[14], p[15], p[17]
        if not lat or not lon:
            continue
        if fc in KEEP_CLASSES and code not in EXCL_CODES:
            pass
        elif fc == 'P' and code in KEEP_PCODES:
            pass
        else:
            continue
        # Limpiar tabs internos en campos de texto
        name = name.replace('\t', ' ')
        ascii_n = ascii_n.replace('\t', ' ')
        pop = pop or '0'
        elev = elev or ''
        tmp.write(f'{gid}\t{name}\t{ascii_n}\t{lat}\t{lon}\t{fc}\t{code}\tVE\t{pop}\t{elev}\t{tz}\n')
        count += 1
tmp.close()
print(f'Registros filtrados: {count}')

def run(sql, label=''):
    r = subprocess.run(
        ['psql', '-h', HOST, '-p', PORT, '-U', 'postgres', '-d', 'buscador', '-c', sql],
        capture_output=True, env=env)
    out = (r.stdout + r.stderr).decode('utf-8', 'replace').strip()
    print(f'[{label}] {out[:120]}')
    return r.returncode

# COPY via stdin
copy_sql = "COPY buscador.geonames(geonameid,name,asciiname,latitude,longitude,feature_class,feature_code,country_code,population,elevation,timezone) FROM STDIN WITH (FORMAT text, DELIMITER '\t', NULL '')"
with open(tmp.name, 'rb') as fh:
    r = subprocess.run(
        ['psql', '-h', HOST, '-p', PORT, '-U', 'postgres', '-d', 'buscador', '-c', copy_sql],
        stdin=fh, capture_output=True, env=env)
print('[COPY]', (r.stdout + r.stderr).decode('utf-8', 'replace').strip()[:120])
os.unlink(tmp.name)

# Geometria
run("UPDATE buscador.geonames SET the_geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) WHERE the_geom IS NULL", 'UPDATE GEOM')

# Indices
run("CREATE INDEX IF NOT EXISTS geonames_geom_idx ON buscador.geonames USING GIST (the_geom)", 'IDX GIST')
run("CREATE INDEX IF NOT EXISTS geonames_name_trgm ON buscador.geonames USING GIN (name gin_trgm_ops)", 'IDX GIN name')
run("CREATE INDEX IF NOT EXISTS geonames_ascii_trgm ON buscador.geonames USING GIN (asciiname gin_trgm_ops)", 'IDX GIN ascii')
run("CREATE INDEX IF NOT EXISTS geonames_fc_idx ON buscador.geonames USING btree (feature_class)", 'IDX fc')

# Stats
run("SELECT feature_class, COUNT(*) FROM buscador.geonames GROUP BY feature_class ORDER BY COUNT(*) DESC", 'STATS')
run("VACUUM ANALYZE buscador.geonames", 'VACUUM')
print('DONE')

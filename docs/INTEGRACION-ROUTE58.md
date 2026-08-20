# Integración Search58 ↔ Route58

Guía para conectar Search58 como geocodificador de Route58 en el entorno QA y producción.

---

## Prerequisitos

- Search58 corriendo en QA: `http://100.75.222.2:7171` (acceso por Tailscale)
- Endpoint `/health` responde `{"status":"ok","db":"connected"}`
- Route58 accesible en el mismo servidor o con acceso a la red Tailscale

Verificar antes de proceder:

```bash
curl http://100.75.222.2:7171/health
curl "http://100.75.222.2:7171/reverse?lat=10.4806&lon=-66.9036"
```

---

## Configuración en Route58

Route58 usa la misma configuración de geocodificador que Traccar. El cambio es en `traccar.xml`:

### 1. Localizar el archivo de configuración

```bash
# Dentro del contenedor de Route58
docker exec <contenedor-route58> find / -name "traccar.xml" 2>/dev/null
# Típicamente en: /opt/traccar/conf/traccar.xml
```

### 2. Editar las entradas del geocodificador

```xml
<!-- traccar.xml -->

<!-- Tipo: nominatim (Search58 es compatible con el formato Nominatim) -->
<entry key='geocoder.type'>nominatim</entry>

<!-- URL de Search58 en QA -->
<entry key='geocoder.url'>http://100.75.222.2:7171</entry>

<!-- Parámetro requerido por el formato Nominatim -->
<entry key='geocoder.key'></entry>
```

> **Nota:** `geocoder.type=nominatim` es correcto aunque Search58 no sea Nominatim. Route58 solo necesita que el endpoint responda en formato Nominatim, que es exactamente lo que hace Search58.

### 3. Reiniciar Route58

```bash
docker restart <contenedor-route58>
```

### 4. Verificar que Route58 usa Search58

Revisar los logs de Search58 mientras Route58 recibe posiciones GPS:

```bash
docker logs infra-search58-api-1 -f | grep reverse
```

Cada punto GPS bautizado genera una línea como:
```
INFO: 100.75.222.2:XXXX - "GET /reverse?lat=10.4806&lon=-66.9036 HTTP/1.1" 200 OK
```

---

## Comportamiento esperado

### Punto en zona urbana con cobertura F58

```
Route58 → GET /reverse?lat=10.4806&lon=-66.9036
Search58 → consulta BD F58 → score 23/25
← "Avenida Nueva Granada entre... La Bandera. Caracas. ... Venezuela."
   source: f58
```

Route58 muestra la dirección detallada a nivel de calle.

### Punto en zona sin cobertura F58

```
Route58 → GET /reverse?lat=10.5989&lon=-66.7391
Search58 → F58 score 5/25 (solo parroquia/municipio)
         → consulta Photon → score 25/25 (tiene calle + ciudad)
← "R-10. Descansadero. Naiguatá. Estado Vargas. Venezuela."
   source: photon
```

Route58 muestra la dirección de Photon (OSM).

### Punto en el mar o zona costera

```
Route58 → GET /reverse?lat=11.5&lon=-67.0
Search58 → tiletype=0 (zona territorial insular)
← "Territorio Insular Francisco de Miranda. Venezuela."
   source: f58
```

Route58 muestra la denominación oficial del territorio.

---

## Campos de la respuesta

Search58 devuelve los mismos campos que Nominatim. Route58 los interpreta sin ningún cambio:

| Campo | Descripción |
|---|---|
| `display_name` | Dirección completa para mostrar en la UI |
| `lat`, `lon` | Coordenadas del punto geocodificado |
| `address.road` | Nombre de la vía |
| `address.city` | Ciudad |
| `address.state` | Estado |
| `address.country` | País |

Campos adicionales de Search58 (Route58 los ignora, útiles para monitoreo):

| Campo | Descripción |
|---|---|
| `source` | Fuente que resolvió: `f58`, `photon` o `nominatim` |
| `score` | Score de completitud de la dirección (0–25) |
| `f58_score` | Score F58 antes del fallback (solo cuando `source != f58`) |

---

## Resiliencia

Search58 está configurado con `restart: unless-stopped`. Si el contenedor cae y se reinicia, Route58 lo detectará en la siguiente petición.

Si la BD PostgreSQL no está disponible (improbable con `depends_on: postgres: condition: service_healthy`), Search58 intenta Photon y Nominatim como fallback antes de devolver error. Route58 nunca recibe un 500 por falta de datos geoespaciales.

---

## Ajuste de rendimiento

Por defecto Search58 llama a fuentes externas (Photon/Nominatim) solo cuando F58 no tiene datos suficientes. Para Venezuela, **~95% de los puntos los resuelve F58 directamente** en ~475ms.

Si se necesita mayor throughput:

```bash
# En el servidor, editar /opt/search58/.env
HYBRID_THRESHOLD=20  # Exigir más completitud antes de devolver F58 directo
                     # (más llamadas a Photon, mayor calidad, mayor latencia)
# o
HYBRID_THRESHOLD=10  # Más permisivo (mayor velocidad, menor detalle)
```

Después de cambiar:
```bash
docker compose --env-file /opt/search58/.env -f /opt/search58/infra/docker-compose.yml up -d
```

---

## Verificación end-to-end

1. **Abrir Route58** con un dispositivo GPS activo
2. En el historial o vista de posiciones, verificar que aparece la dirección
3. **Comparar** con `http://100.75.222.2:7171/geocode-compare.html` — ingresar las coordenadas del punto y comparar el resultado de Search58 con Nominatim/Photon directos

---

## Monitoreo

```bash
# Ver últimas peticiones en tiempo real
docker logs infra-search58-api-1 -f

# Estadísticas rápidas (últimas 100 peticiones)
docker logs infra-search58-api-1 --tail 200 | grep '"GET /reverse' | wc -l

# Peticiones que usaron Photon o Nominatim (F58 no cubrió)
docker logs infra-search58-api-1 --tail 500 | grep '"GET /reverse'
```

Para ver qué fuente usó cada petición, usar el comparador visual o consultar directamente:

```bash
curl "http://100.75.222.2:7171/reverse?lat=<lat>&lon=<lon>" | python3 -m json.tool | grep source
```

---

## Benchmark

Medir el throughput real desde el servidor de Route58:

```bash
# Desde el mismo servidor QA
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{time_total}s\n" \
    "http://100.75.222.2:7171/reverse?lat=10.4806&lon=-66.9036"
done
```

O con el script incluido en el repo (desde la máquina de desarrollo):

```bash
python benchmark.py --url http://100.75.222.2:7171 --n 200 --workers 10
```

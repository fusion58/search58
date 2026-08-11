from contextlib import asynccontextmanager
import os
import httpx
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from geocoder import geocode_hybrid, search_places, sample_points
from db import run_sql

GEOSERVER_URL = os.environ.get('GEOSERVER_URL', 'http://localhost:8080')


@asynccontextmanager
async def lifespan(app: FastAPI):
    # El pool se inicializa en el primer request (lazy).
    # No conectar aquí: sin BD en el env de smoke test, startup fallaría.
    yield


app = FastAPI(title='Search58', version='1.0', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['GET'],
    allow_headers=['*'],
)


@app.get('/health')
def health():
    try:
        run_sql('SELECT 1')
        return {'status': 'ok', 'db': 'connected'}
    except Exception as e:
        raise HTTPException(status_code=503, detail={'status': 'error', 'db': str(e)})


@app.get('/reverse')
def reverse(
    lat: float = Query(..., description='Latitud WGS84'),
    lon: float = Query(..., description='Longitud WGS84'),
):
    return geocode_hybrid(lat, lon)


@app.get('/search')
def search(
    q:     str = Query(..., min_length=3),
    limit: int = Query(10, ge=1, le=50),
):
    return search_places(q, limit)


@app.get('/sample-points')
def get_sample_points(n: int = Query(100, ge=1, le=500)):
    return sample_points(n)


@app.api_route('/geoserver/{path:path}', methods=['GET', 'HEAD'])
def proxy_geoserver(path: str, request: Request):
    url = f'{GEOSERVER_URL}/geoserver/{path}'
    qs = str(request.url.query)
    if qs:
        url += '?' + qs
    with httpx.Client(timeout=15, follow_redirects=True) as client:
        resp = client.request(request.method, url, headers={'Host': 'localhost'})
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get('content-type'),
        headers={'Access-Control-Allow-Origin': '*'},
    )


app.mount('/', StaticFiles(directory='frontend', html=True), name='frontend')

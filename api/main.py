from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from geocoder import geocode_hybrid, search_places
from db import run_sql, get_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_pool()   # inicializar el pool al arrancar
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
    q:     str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
):
    return search_places(q, limit)

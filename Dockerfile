FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ .
COPY frontend/geocode-compare.html frontend/f58-style.js frontend/maki-icons.js frontend/

EXPOSE 7171

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7171", "--workers", "4"]

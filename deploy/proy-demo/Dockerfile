# Runtime exacto del SVM PROY para la demo: Linux/amd64 (staging) y Linux/aarch64,
# ambas tuplas registradas en docs/PROY_SVM_COMPATIBILIDAD_X86_64.json. El build
# falla si el artefacto no carga o si la probabilidad de control se sale de
# tolerancia, asi que una imagen que responderia 503 no llega a construirse.
FROM python:3.12.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app

COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
COPY deploy/proy-demo/constraints.txt ./constraints.txt

# Las restricciones fijan el stack del SVM desde la primera resolucion, sin
# instalar una version y degradarla despues.
RUN pip install --upgrade pip \
 && pip install -c constraints.txt .

COPY deploy/proy-demo/check-runtime.py ./check-runtime.py
RUN python check-runtime.py

USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

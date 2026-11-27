# Runtime exacto del SVM PROY para la demo: Linux/aarch64 (candidato registrado
# en docs/PROY_SVM_COMPATIBILIDAD.json). El build falla si el artefacto no carga
# o si la probabilidad de control se sale de tolerancia, asi que una imagen que
# responderia 503 no llega a construirse.
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

# Las versiones del SVM se fijan despues de las dependencias de la app para que
# pip no las sustituya por las ultimas al resolver el proyecto.
RUN pip install --upgrade pip \
 && pip install . \
 && pip install \
      "numpy==2.5.3" \
      "scikit-learn==1.9.1" \
      "scipy==1.18.1" \
      "joblib==1.6.0" \
      "threadpoolctl==3.7.0"

COPY deploy/proy-demo/check-runtime.py ./check-runtime.py
RUN python check-runtime.py

USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

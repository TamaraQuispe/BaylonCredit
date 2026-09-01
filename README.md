# BaylonCredit IA

Sistema de gestión de ventas, créditos, pagos y evaluación crediticia para Cervecería Baylón.

## Arquitectura

- Frontend: React, TypeScript, Vite y Tailwind CSS.
- API: FastAPI asíncrono, SQLAlchemy 2 y JWT.
- Base de datos: PostgreSQL 17 con migraciones Alembic.
- Ejecución: imágenes Docker independientes para frontend y API.
- Operación: health checks, logs con `request_id`, configuración por entorno y CI en GitHub Actions.

El diseño no depende de un proveedor específico. Las mismas imágenes pueden desplegarse en AWS, Google Cloud, Azure, Render, Railway u otra plataforma compatible con contenedores.

## Inicio Rápido Con Docker

1. Crea la configuración local:

```bash
cp .env.example .env
```

2. Sustituye las contraseñas y el secreto JWT de `.env`.

3. Construye y levanta PostgreSQL, migraciones, API y frontend:

```bash
docker compose up --build -d
```

4. Crea el primer administrador:

```bash
docker compose exec \
  -e ADMIN_EMAIL=admin@baylon.com \
  -e ADMIN_PASSWORD='una-clave-segura-de-10-caracteres' \
  -e ADMIN_FULL_NAME='Administrador Baylon' \
  api python -m app.scripts.create_admin
```

5. Abre `http://localhost:8080`. La API queda disponible en `http://localhost:8000` y Swagger en `http://localhost:8000/docs` fuera de producción.

## Desarrollo Frontend

```bash
npm install
npm run dev
npm run build
npm run lint
```

Define `VITE_API_URL=http://localhost:8000/api/v1` para apuntar al backend local.

## Desarrollo Backend

Requiere Python 3.12 o 3.13 y PostgreSQL.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Validaciones:

```bash
ruff check .
pytest
```

## Endpoints Iniciales

- `GET /health/live`: proceso activo.
- `GET /health/ready`: API y PostgreSQL disponibles.
- `POST /api/v1/auth/login`: autenticación OAuth2 con email y contraseña.
- `GET /api/v1/auth/me`: usuario autenticado.
- `GET|POST /api/v1/users`: administración de usuarios y roles.
- `PATCH /api/v1/users/{id}/status`: activar o desactivar usuarios.
- `GET|POST|PATCH|DELETE /api/v1/clients`: gestión de clientes con archivado lógico.
- `GET|POST|PATCH|DELETE /api/v1/products`: catálogo persistente de productos.
- `POST /api/v1/products/{id}/stock`: entradas y ajustes auditables de inventario.
- `GET|POST /api/v1/sales`: consulta y registro transaccional de ventas.
- `POST /api/v1/credits/evaluate`: evaluación de riesgo y límite recomendado.
- `GET|POST /api/v1/credits`: cartera, detalle, historial y fiados directos.
- `GET|POST /api/v1/payments`: abonos totales o parciales con asignaciones atómicas.

Roles disponibles: `admin`, `operator` y `viewer`.

Al registrar una venta, la API bloquea los productos implicados, valida existencias, recalcula precios e IGV y descuenta stock dentro de una única transacción. Una venta fiada evalúa el riesgo y crea el crédito en esa misma operación; si cualquier validación falla, no se persiste ningún cambio.

## Migraciones

No se crean tablas automáticamente al arrancar la API. En cada despliegue debe ejecutarse una sola tarea de release antes de iniciar las réplicas:

```bash
cd backend
alembic upgrade head
```

Para generar una migración después de cambiar los modelos:

```bash
alembic revision --autogenerate -m "descripcion"
```

## Despliegue En La Nube

- Construye `Dockerfile` para el frontend y `backend/Dockerfile` para la API.
- Usa PostgreSQL administrado con backups, alta disponibilidad y conexiones cifradas.
- Guarda `DATABASE_URL`, `JWT_SECRET_KEY` y credenciales en el gestor de secretos del proveedor.
- Configura `ENVIRONMENT=production` y los dominios permitidos en `CORS_ORIGINS`.
- Ejecuta `alembic upgrade head` como tarea de release, no desde cada réplica.
- Apunta los probes del orquestador a `/health/live` y `/health/ready`.
- Termina HTTPS en el balanceador y conserva `X-Forwarded-*` hacia la API.
- Publica el frontend en CDN o usa su imagen Nginx.

No deben incluirse archivos `.env`, secretos ni datos de producción en Git.

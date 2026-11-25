# PROY - Matriz de trazabilidad

| Requisito PROY | Archivo/seccion | Prueba | Evidencia | Estado |
|---|---|---|---|---|
| Regla saldo cero | backend/app/services/proy_credit_policy.py | test_proy_credit_protocol.py | commit 38165be | HECHO |
| Concurrencia/idempotencia | backend/app/services/idempotency.py; credits.py; sales.py | test_proy_concurrency_postgres.py | commit cc76d6e | HECHO |
| Contrato features/target | backend/app/ml/proy_contract.py | test_proy_contract.py | commit 1779555 | HECHO |
| Cuatro modelos taller | backend/scripts/proy_credit_experiment_v1.py | ejecucion protocolo | commit 76e4240 | HECHO |
| Cola revision humana | backend/app/services/credit_review.py; credits.py | tests backend | commit 9c106af | HECHO |
| Frontend cola | src/pages/RevisionesCreditoPage.tsx | build frontend | commit b813595 | HECHO |
| Privacidad/piloto | docs/PROY_PRIVACIDAD_PILOTO.md | revision documental | commit c08d91f | HECHO |
| Despliegue/rollback | docs/PROY_DESPLIEGUE_ROLLBACK.md | checklist | commit c08d91f | HECHO |
| Endpoint operativo scoring | /credits/evaluate (snapshot servidor) | tests credit policy | HECHO |
| Validacion comercial real | piloto autorizado | pendiente | pendiente | PENDIENTE |
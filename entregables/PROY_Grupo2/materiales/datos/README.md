# Datos De V6 Final

Copias exactas de los CSV congelados. Datos 100 % simulados, no clientes reales.
No se genero ni entreno nada al organizar esta carpeta.

| Archivo | Filas | Etiquetas conocidas | Desconocidas | Fuente original |
| --- | ---: | ---: | ---: | --- |
| desarrollo.csv | 541 | 534 | 7 | development/development_eligible.csv |
| desarrollo_etiquetado.csv | 534 | 534 | 0 | development/development_known.csv |
| final.csv | 277 | 275 | 2 | experiment/final_eligible.csv |
| historial_desarrollo.csv | 631 | 624 | 7 | development/development_raw.csv |
| historial_final.csv | 322 | 320 | 2 | experiment/final_raw.csv |

`desarrollo.csv` y `final.csv` contienen solo fiados elegibles de study: deuda cero
e historial pagado. `desarrollo_etiquetado.csv` es la parte conocida usada para ajustar.
FINAL no se usa para entrenar ni elegir modelos. Etiquetas vacias no se convierten en cero;
compiten por capacidad si son elegibles, pero no entran en metricas supervisadas.

Los historiales completos incluyen warmup: NO son datasets listos para entrenamiento.
Las solicitudes bloqueadas no son fiados otorgados ni aparecen como clase cero en estos CSV.
Sus registros estan en development/development_routing_ledger.json y
experiment/final_routing_ledger.json. Ningun bloqueo o revision humana es un acierto ML.

Diccionario de las 24 columnas, once predictores, conteos, fuentes y hashes:
`diccionario.json`. No usar IDs, fechas, scenario o pending_at_cutoff como predictores.
Los originales se conservan sin cambios en development/ y experiment/.

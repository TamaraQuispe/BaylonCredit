# APF3 Resultados V6 Final

SVM elegida por F2 OOF de politica 0.55236729, frente al arbol 0.54607509. FINAL SVM: F2 0.60606061, precision 0.32000000, recall 0.78048780 (32/41). El arbol logra F2 FINAL 0.64315353; no se reselecciona con el test.

| Fase estudio | Intentos | Bloqueos | Manual | Elegibles | Conocidos | Clases 0/1 | ? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DEV | 586 | 45 | 0 | 541 | 534 | 448/86 | 7 |
| FINAL | 292 | 15 | 0 | 277 | 275 | 234/41 | 2 |

SVM: 100 revisiones frente a 274 de Dummy positivo limitado. 174 menos x 2 minutos = 348 minutos HIPOTETICOS, no ahorro observado. Los FN pasan de 0 en Dummy limitado a 9 en SVM; 68 FP tambien consumen tiempo. No hay ganancias garantizadas.

V6 Final r1 es revision prospectiva tras consultar V6 historico, que se conserva. Simulador y supuestos sin cambios; semillas nuevas 2026112601/02/03 y clientes disjuntos. Sin targets desconocidos imputados a cero. Gates separados de accuracy; cero manuales de estudio por warmup. Siete pruebas independientes de gates sin llamada al modelo.

| Modelo | Particion | Precision | Recall | F1 | F2 | Accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| SVM elegida | final | 0.32000000 | 0.78048780 | 0.45390071 | 0.60606061 | 0.72000000 |
| Arbol | final | 0.40259740 | 0.75609756 | 0.52542373 | 0.64315353 | 0.79636364 |
| Dummy mayoria | final | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.85090909 |
| Dummy positivo | final | 0.14909091 | 1.00000000 | 0.25949367 | 0.46697039 | 0.14909091 |

## Politica FINAL

| Modelo | Particion | Precision | Recall | F1 | F2 | Accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| SVM elegida | final | 0.32000000 | 0.78048780 | 0.45390071 | 0.60606061 | 0.72000000 |
| Arbol | final | 0.40259740 | 0.75609756 | 0.52542373 | 0.64315353 | 0.79636364 |
| Dummy mayoria | final | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.85090909 |
| Dummy positivo | final | 0.15073529 | 1.00000000 | 0.26198083 | 0.47018349 | 0.16000000 |

Matriz SVM [[166,68],[9,32]]. OOF seleccionado conserva optimismo; calibracion interna agrupada no es evaluacion anidada de toda la seleccion. coherence_accepted=false; revision de 23 elementos V5 no equivale a aprobacion de filas nuevas. Doce clientes son roster de ejemplo.

Informe: 16 paginas PDF, portada + 12 cuerpo + referencias + 2 anexos. Sustentacion: 13 diapositivas editables y 13 paginas PDF; guion: 3 paginas PDF. Texto y bounds offline verificados. Contenido Word/PPTX, saltos Word y geometria PPTX verificados; no renderizados por Microsoft Office.

Estado tecnico consultable en manifiesto. No se acredita nuevo despliegue ni reproduccion; produccion intacta. Revision de cuatro integrantes y ensayo pendientes, sin roles ni firmas confirmados.

Salidas: /Users/tamaraalison/Downloads/APF3_Grupo2_V6_Final/informe y sustentacion. Verificacion: informe/verificacion-documentos.json; SHA-256: informe/manifiesto-archivos.json.

Comando desde la raiz del repositorio:

```bash
/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/apf3-informe-venv/bin/python deploy/generate-v6-final-documents.py
```

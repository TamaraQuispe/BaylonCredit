"""Render the supplied cost report faithfully for Word annexes."""

import sys
from pathlib import Path

import pymupdf

source, output = Path(sys.argv[1]), Path(sys.argv[2])
output.mkdir(parents=True, exist_ok=True)
with pymupdf.open(source) as pdf:
    for index, page in enumerate(pdf):
        page.get_pixmap(matrix=pymupdf.Matrix(1.2, 1.2)).save(output / f"oracle-costos-pagina-{index + 1}.png")
    print(f"Reporte original conservado; {len(pdf)} paginas renderizadas.")

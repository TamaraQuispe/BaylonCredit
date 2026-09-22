from pathlib import Path

import numpy as np

from app.ml.features import FEATURE_NAMES

MINIMUM_ROWS = 30


def load_real_dataset(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = np.atleast_1d(
        np.genfromtxt(path, delimiter=",", names=True, dtype=float, encoding="utf-8")
    )
    required = {*FEATURE_NAMES, "defaulted"}
    found = set(data.dtype.names or ())
    missing = required - found
    if missing:
        raise ValueError(f"Faltan columnas: {', '.join(sorted(missing))}")
    if len(data) < MINIMUM_ROWS:
        raise ValueError(f"Se requieren al menos {MINIMUM_ROWS} desenlaces reales; hay {len(data)}")
    y = np.asarray(data["defaulted"], dtype=int)
    if set(y) != {0, 1}:
        raise ValueError("El dataset debe tener pagos al día (0) y atrasos/impagos (1)")
    counts = np.bincount(y, minlength=2)
    if counts.min() < 5:
        raise ValueError("Se requieren al menos 5 casos reales por clase para validar el modelo")
    x = np.column_stack([np.asarray(data[name], dtype=float) for name in FEATURE_NAMES])
    return x, y

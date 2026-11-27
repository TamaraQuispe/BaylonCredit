"""Falla si el entorno actual no puede cargar el SVM PROY verificado.

Se usa como paso de build de la imagen demo y como comprobacion manual de
cualquier venv: si esto no pasa, el endpoint experimental respondera 503.
"""

import sys

from app.ml.proy_model import MODEL_VERSION, ProyModelUnavailable, _load

# Fila de control de la evidencia: ambos runtimes verificados difieren ~2e-14.
ILLUSTRATIVE = [6, 6, 1, 0, 0, 0, 0, 0.25, 180, 5 / 6, 0]
EXPECTED_PROBABILITY = 0.13741099608146
TOLERANCE = 1e-9


def main() -> int:
    try:
        model = _load()
        probability = float(model.predict_proba([ILLUSTRATIVE])[0, 1])
    except ProyModelUnavailable as exc:  # runtime, hash, metadata o artefacto
        print(f"RUNTIME_NO_APTO: {exc}", file=sys.stderr)
        return 1
    if abs(probability - EXPECTED_PROBABILITY) > TOLERANCE:
        print(
            f"RUNTIME_NO_APTO: probabilidad {probability!r} fuera de tolerancia",
            file=sys.stderr,
        )
        return 1
    print(f"RUNTIME_OK {MODEL_VERSION} prob={probability:.15f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

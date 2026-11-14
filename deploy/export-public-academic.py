"""Export reviewed synthetic deliverables without changing original local evidence."""

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

REPO = Path(__file__).resolve().parents[1]


def copy_checked(source: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if source.read_bytes() != destination.read_bytes():
            raise ValueError(
                f"Public copy already differs; review before replacing: {destination}"
            )
        return
    shutil.copyfile(source, destination)


def export(downloads: Path):
    public = REPO / "entregables"
    archive = downloads / "APF3_Grupo2_CV_Agrupada_V3.zip"
    cv3 = public / "APF3_CV3"
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        prefix = archive.stem + "/"
        manifest = json.loads(zipped.read(prefix + "manifest.json"))
        for item in zipped.infolist():
            if item.is_dir():
                continue
            assert item.filename.startswith(prefix)
            relative = item.filename[len(prefix) :]
            path = PurePosixPath(relative)
            assert not path.is_absolute() and ".." not in path.parts
            assert item.file_size < 50_000_000
            content = zipped.read(item)
            if relative != "manifest.json":
                assert hashlib.sha256(content).hexdigest() == manifest[relative], (
                    relative
                )
            target = cv3.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.read_bytes() == content, (
                    f"Existing public file differs: {relative}"
                )
            else:
                target.write_bytes(content)
    copy_checked(archive, public / archive.name)
    completed = downloads / "APF3_Ficha_Propietario_Baylon.docx"
    if not completed.exists():
        completed = (
            downloads / "APF3_Grupo2_CV_Agrupada_V3" / "sustentacion"
            / "APF3_Ficha_Propietario_Baylon.docx"
        )
    if completed.exists():
        with zipfile.ZipFile(completed) as zipped:
            tree = ElementTree.fromstring(zipped.read("word/document.xml"))
        text = " ".join(" ".join(tree.itertext()).lower().split())
        assert "caso totalmente simulado" in text
        assert "no constituye testimonio ni entrevista" in text
        copy_checked(completed, cv3 / "escenarios/Ficha_Hipotetica_Completada.docx")
        note = cv3 / "escenarios/README.md"
        if not note.exists():
            note.write_text(
                "# Ficha hipotética completada\n\n"
                "Este documento declara que es totalmente simulado: usa cálculos de final.csv "
                "y respuestas complementarias hipotéticas. No acredita entrevista, aprobación "
                "ni capacidad real del propietario y no calibra de forma independiente el "
                "simulador del que procede ese mismo CSV.\n\n"
                "Las reglas nuevas (por ejemplo un límite inicial de S/ 25, horarios, gracia, "
                "posible incobrabilidad o cinco revisiones al día) son propuestas del escenario, "
                "no reglas implementadas ni confirmadas del experimento CV3. Sus resultados "
                "congelados no se modifican con esta ficha.\n\n"
                "La plantilla pendiente de respuestas reales se conserva en sustentacion. "
                "La copia recibida y los originales locales no se han sobrescrito.\n"
            )
    workshop = downloads / "S14B_TallerML_Grupo2_Colab"
    verification = json.loads((workshop / "verificacion-ejecucion.json").read_text())
    notebook = workshop / "S14A_TallerML_Grupo2_Colab.ipynb"
    assert (
        hashlib.sha256(notebook.read_bytes()).hexdigest()
        == verification["notebook_sha256"]
    )
    for filename in (
        "README.md",
        "requirements.txt",
        notebook.name,
        "verificacion-ejecucion.json",
    ):
        copy_checked(workshop / filename, public / "taller_s14" / filename)
    pilot = downloads / "APF3_Grupo2_Piloto_Sintetico"
    for directory, report_name in (
        ("ejecucion-02", "academic_synthetic_report.json"),
        ("experimento-v2", "experiment_v2_report.json"),
    ):
        report = json.loads((pilot / directory / report_name).read_text())
        assert report["data_source"] == "synthetic"
        for file in (pilot / directory).rglob("*"):
            if file.is_file() and file.suffix in {
                ".json",
                ".csv",
                ".joblib",
                ".png",
                ".md",
            }:
                copy_checked(
                    file,
                    public
                    / "piloto_sintetico"
                    / directory
                    / file.relative_to(pilot / directory),
                )
    (public / "piloto_sintetico/README.md").write_text(
        "# Experimentos sintéticos previos\n\n"
        "Ejecución-02 y experimento-v2 son antecedentes congelados. No contienen operaciones "
        "reales y no sustituyen CV3. Sus tests ya se consultaron; no reutilizarlos para "
        "seleccionar nuevos candidatos. La ejecución-01 descartada no se publica "
        "como evidencia vigente.\n\n"
        "El laboratorio web v2 requiere cargar sus artefactos confiables en el volumen "
        "privado ./academic del despliegue de demo. Esta carpeta pública no es ese volumen "
        "y no se monta automáticamente en producción. No entrenar en el servidor público.\n"
    )
    failures = downloads / "APF3_Grupo2_Pruebas_Fallos_Backend"
    result = json.loads((failures / "fallos-backend-reales.json").read_text())
    assert len(result["results"]) == 6 and all(
        item["passed"] for item in result["results"]
    )
    for file in failures.iterdir():
        if file.is_file() and file.suffix in {".json", ".png", ".docx", ".md"}:
            copy_checked(file, public / "fallos_backend" / file.name)
    files = [file for file in public.rglob("*") if file.is_file()]
    assert all(file.stat().st_size < 50_000_000 for file in files)
    print(
        json.dumps(
            {
                "published_files": len(files),
                "bytes": sum(file.stat().st_size for file in files),
                "source_archive_verified": True,
                "originals_modified": False,
                "completed_form_scope": "hypothetical scenario, not owner evidence",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--downloads", type=Path, required=True)
    export(parser.parse_args().downloads)

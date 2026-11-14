"""Verify preparation artifacts without training or evaluating the final dataset."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from docx import Document
from PIL import Image, ImageOps
from pptx import Presentation
from pypdf import PdfReader

NAME = "APF3_TD_Grupo2_ML_Innovacion"


def verify(root: Path):
    output = root / "sustentacion"
    plan = json.loads((output / "plan-sustentacion.json").read_text())
    report_path = root / "experimento/grouped_cv_report.json"
    report = json.loads(report_path.read_text())
    assert (
        hashlib.sha256(report_path.read_bytes()).hexdigest()
        == plan["source_report_sha256"]
    )
    assert plan["slides"] == 13 and plan["planned_seconds"] == 720
    assert sum(plan["planned_speaker_seconds"].values()) == 720
    assert set(plan["planned_speaker_seconds"]) == {"Omara", "César", "Tamara", "Pablo"}
    assert plan["live_inference_reserved_seconds"] == 50
    presentation = Presentation(output / (NAME + ".pptx"))
    assert len(presentation.slides) == 13
    for index, slide in enumerate(presentation.slides):
        assert (
            f"**Tiempo:** {plan['slides_data'][index]['seconds']} s"
            in slide.notes_slide.notes_text_frame.text
        )
        for shape in slide.shapes:
            assert shape.left >= 0 and shape.top >= 0
            assert shape.left + shape.width <= presentation.slide_width + 1000
            assert shape.top + shape.height <= presentation.slide_height + 1000
    table = next(
        shape.table for shape in presentation.slides[6].shapes if shape.has_table
    )
    assert len(table.rows) == 5 and len(table.columns) == 6
    for index, family in enumerate(("tree", "svm", "most_frequent", "constant_1"), 1):
        for column, metric in enumerate(
            ("precision", "recall", "f1", "f2", "accuracy"), 1
        ):
            assert table.cell(
                index, column
            ).text == f"{report['models'][family]['final'][metric]:.4f}".replace(
                ".", ","
            )
    slide_pdf = PdfReader(output / (NAME + ".pdf"))
    assert len(slide_pdf.pages) == 13
    text = "\n".join(page.extract_text() for page in slide_pdf.pages)
    for code in ("U23204737", "U23231338", "U23259768", "U23251279"):
        assert code in text
    assert "11,90" in text and "0,7311" in text
    assert not json.loads((output / "revision-diseno.json").read_text())["overflows"]
    supporting = {}
    for name in (
        "APF3_Grupo2_Guion_12min",
        "APF3_Grupo2_Ficha_Calibracion_Meta",
        "APF3_Ficha_Propietario_Baylon",
    ):
        editable = Document(output / (name + ".docx"))
        assert len(editable.paragraphs) > 20
        pdf = PdfReader(output / (name + ".pdf"))
        assert len(pdf.pages) > 0
        supporting[name] = len(pdf.pages)
    form_text = "\n".join(
        page.extract_text()
        for page in PdfReader(output / "APF3_Grupo2_Ficha_Calibracion_Meta.pdf").pages
    )
    assert "POR COMPLETAR" in " ".join(form_text.split()) and re.search(
        r"_{5,}", form_text
    )
    assert "PENDIENTE" in form_text
    demo = json.loads(
        (output / "evidencias/demo_inferencia_preparacion.json").read_text()
    )
    assert demo == report["illustrative_inference"]
    assert demo["known_label"] is None and demo["research_only"]
    contact = Image.new("RGB", (1280, 720), "#e3e6e9")
    for index in range(13):
        with Image.open(output / "vistas" / f"{index + 1:02}.png") as image:
            thumb = ImageOps.contain(image, (316, 176))
            contact.paste(thumb, ((index % 4) * 320 + 2, (index // 4) * 180 + 2))
    contact.save(output / "vista-general.png")
    result = {
        "passed": True,
        "editable_ppt_slides": 13,
        "presentation_pdf_pages": 13,
        "planned_seconds": 720,
        "planned_speaker_seconds": plan["planned_speaker_seconds"],
        "spoken_words": plan["spoken_words"],
        "supporting_pdf_pages": supporting,
        "all_final_metrics_match_frozen_report": True,
        "demo_preparation_output_matches_verified_inference": True,
        "new_final_dataset_predictions": False,
        "human_rehearsal": "Pending",
        "native_ppt_visual_review": "Review in presentation editor still required",
        "pdf_rendering": "Shared slide design rendered offline; not native PPT conversion",
    }
    (output / "verificacion-sustentacion.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    verify(parser.parse_args().root)

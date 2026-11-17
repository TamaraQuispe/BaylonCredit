"""Export supplied slide elements as editable PowerPoint and matching offline HTML."""

import base64
import html
import math
import mimetypes
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

NAVY, PAPER, INK = "10283F", "F6F3EB", "172B3A"


def export_slides(
    deck: list[dict],
    output: Path,
    name: str = "APF3_TD_Grupo2_ML_Innovacion",
    version: str = "V4",
) -> None:
    """Write output/name.{pptx,html}; metadata never adds visible slide content."""
    presentation = Presentation()
    presentation.slide_width, presentation.slide_height = Inches(13.333333), Inches(7.5)
    presentation.core_properties.title = f"{name} {version}"
    rendered = []
    for item in deck:
        dark = item.get("dark", False)
        bg = NAVY if dark else PAPER
        native = presentation.slides.add_slide(presentation.slide_layouts[6])
        native.background.fill.solid()
        native.background.fill.fore_color.rgb = RGBColor.from_string(bg)
        native.notes_slide.notes_text_frame.text = item.get("notes", "")
        elements = []
        for element in item["elements"]:
            x, y, w, h = (element[key] for key in ("x", "y", "w", "h"))
            if not (
                all(math.isfinite(value) for value in (x, y, w, h))
                and x >= 0
                and y >= 0
                and w > 0
                and h > 0
                and x + w <= 13.333333 + 1e-6
                and y + h <= 7.5 + 1e-6
            ):
                raise ValueError(f"Slide {item['number']}: out-of-bounds element {element}")
            bounds = (Inches(x), Inches(y), Inches(w), Inches(h))
            style = f"left:{x * 96}px;top:{y * 96}px;width:{w * 96}px;height:{h * 96}px;"
            kind = element["kind"]
            if kind == "rect":
                fill = element.get("fill", NAVY)
                shape = native.shapes.add_shape(MSO_SHAPE.RECTANGLE, *bounds)
                shape.fill.solid()
                shape.fill.fore_color.rgb = RGBColor.from_string(fill)
                shape.line.fill.background()
                elements.append(f'<div class="shape" style="{style}background:#{fill}"></div>')
            elif kind == "image":
                path = Path(element["path"])
                native.shapes.add_picture(str(path), *bounds)
                image = base64.b64encode(path.read_bytes()).decode("ascii")
                mime = mimetypes.guess_type(path.name)[0] or "image/png"
                elements.append(
                    f'<img class="shape" style="{style}" src="data:{mime};base64,{image}" alt="">'
                )
            elif kind == "text":
                size, bold = element.get("size", 21), element.get("bold", False)
                color = element.get("color") or ("FFFFFF" if dark else INK)
                align = element.get("align", "left")
                alignment = {
                    "left": PP_ALIGN.LEFT,
                    "center": PP_ALIGN.CENTER,
                    "right": PP_ALIGN.RIGHT,
                    "justify": PP_ALIGN.JUSTIFY,
                }[align]
                font = "Consolas" if element.get("mono", False) else "Arial"
                frame = native.shapes.add_textbox(*bounds).text_frame
                frame.word_wrap, frame.auto_size = True, MSO_AUTO_SIZE.NONE
                frame.margin_left = frame.margin_right = 0
                frame.margin_top = frame.margin_bottom = 0
                frame.vertical_anchor = MSO_ANCHOR.TOP
                for index, line in enumerate(element["text"].split("\n")):
                    paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
                    paragraph.text, paragraph.line_spacing = line, 1.08
                    paragraph.space_before = paragraph.space_after = Pt(0)
                    paragraph.alignment = alignment
                    paragraph.font.name, paragraph.font.size = font, Pt(size)
                    paragraph.font.bold = bold
                    paragraph.font.color.rgb = RGBColor.from_string(color)
                fallback = "monospace" if element.get("mono", False) else "sans-serif"
                elements.append(
                    f'<div class="shape txt" style="{style}font:{size}pt/1.08 {font},{fallback};'
                    f'font-weight:{700 if bold else 400};color:#{color};text-align:{align}">'
                    f"{html.escape(element['text'])}</div>"
                )
            elif kind == "table":
                data = [element["headers"], *element["rows"]]
                widths = element["widths"]
                row_height = element["row_height"]
                size = element.get("size", 18)
                if not (
                    widths
                    and all(math.isfinite(width) and width > 0 for width in widths)
                    and all(len(row) == len(widths) for row in data)
                    and math.isfinite(row_height)
                    and row_height > 0
                    and math.isclose(sum(widths), w, rel_tol=0, abs_tol=1e-6)
                    and math.isclose(len(data) * row_height, h, rel_tol=0, abs_tol=1e-6)
                ):
                    raise ValueError(f"Slide {item['number']}: inconsistent table dimensions")
                grid = native.shapes.add_table(len(data), len(widths), *bounds).table
                for column, width in zip(grid.columns, widths, strict=True):
                    column.width = Inches(width)
                html_rows = []
                for row_index, values in enumerate(data):
                    grid.rows[row_index].height = Inches(row_height)
                    fill = NAVY if row_index == 0 else "E1ECE6" if row_index == 1 else "EFE9DF"
                    color = "FFFFFF" if row_index == 0 else INK
                    html_cells = []
                    for column_index, value in enumerate(values):
                        cell = grid.cell(row_index, column_index)
                        cell.text = str(value)
                        cell.fill.solid()
                        cell.fill.fore_color.rgb = RGBColor.from_string(fill)
                        cell.margin_left = cell.margin_right = Inches(0.1)
                        cell.margin_top = cell.margin_bottom = Inches(0.08)
                        cell.vertical_anchor = MSO_ANCHOR.TOP
                        cell.text_frame.word_wrap = True
                        cell.text_frame.auto_size = MSO_AUTO_SIZE.NONE
                        for paragraph in cell.text_frame.paragraphs:
                            paragraph.line_spacing = 1.08
                            paragraph.space_before = paragraph.space_after = Pt(0)
                            paragraph.alignment = PP_ALIGN.LEFT
                            paragraph.font.name, paragraph.font.size = "Arial", Pt(size)
                            paragraph.font.bold = row_index == 0
                            paragraph.font.color.rgb = RGBColor.from_string(color)
                        for edge in ("lnL", "lnR", "lnT", "lnB"):
                            line = OxmlElement(f"a:{edge}", {"w": "9525"})
                            solid = OxmlElement("a:solidFill")
                            solid.append(OxmlElement("a:srgbClr", {"val": PAPER}))
                            line.append(solid)
                            cell._tc.get_or_add_tcPr().append(line)
                        html_cells.append(
                            f'<div style="width:{widths[column_index] * 96}px;'
                            f"background:#{fill};color:#{color};"
                            f'font-weight:{700 if row_index == 0 else 400}">'
                            f"{html.escape(str(value))}</div>"
                        )
                    html_rows.append('<div class="tr">' + "".join(html_cells) + "</div>")
                elements.append(
                    f'<div class="shape tbl" style="{style}font-size:{size}pt;'
                    f'--rh:{row_height * 96}px">' + "".join(html_rows) + "</div>"
                )
            else:
                raise ValueError(f"Unsupported element kind: {kind!r}")
        number = html.escape(str(item["number"]), quote=True)
        rendered.append(
            f'<section class="slide" data-number="{number}" style="background:#{bg}">'
            + "".join(elements)
            + "</section>"
        )
    css = """@page{size:13.333333in 7.5in;margin:0}*{box-sizing:border-box}
body{margin:0;font-family:Arial,sans-serif;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.slide{width:1280px;height:720px;position:relative;break-after:page;overflow:hidden}
.slide:last-child{break-after:auto}.shape{position:absolute}
.txt{white-space:pre-wrap;overflow-wrap:normal}
.tbl .tr{display:flex;height:var(--rh)}
.tbl .tr>div{flex-shrink:0;padding:8px 10px;border:1px solid #f6f3eb;
line-height:1.08;white-space:pre-wrap;overflow-wrap:normal}
"""
    output.mkdir(parents=True, exist_ok=True)
    presentation.save(output / f"{name}.pptx")
    (output / f"{name}.html").write_text(
        '<!doctype html><html lang="es"><head><meta charset="utf-8"><title>'
        + html.escape(f"{name} {version}")
        + "</title><style>"
        + css
        + "</style></head><body>"
        + "".join(rendered)
        + "</body></html>",
        encoding="utf-8",
    )

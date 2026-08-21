"""
modules/certificate_renderer.py
Production PyMuPDF renderer for ODS certificates.
"""
import os
import fitz

A4_WIDTH = 595.28
A4_HEIGHT = 841.89

COURSE_COLOR = (0.75, 0.12, 0.20)

ODS_ABS_LAYOUT = {
    "certificate_no": {
        "x": 420, "y": 40, "max_width": 145, "h": 18, "fontsize": 10, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "student_name": {
        "x": 158, "y": 192, "max_width": 250, "h": 20, "fontsize": 12, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "date_of_birth": {
        "x": 480, "y": 192, "max_width": 85, "h": 18, "fontsize": 11, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "cdc_no": {
        "x": 158, "y": 220, "max_width": 145, "h": 18, "fontsize": 11, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "passport_no": {
        "x": 440, "y": 220, "max_width": 130, "h": 18, "fontsize": 11, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "competency_grade": {
        "x": 245, "y": 240, "max_width": 140, "h": 18, "fontsize": 11, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "competency_no": {
        "x": 425, "y": 240, "max_width": 120, "h": 18, "fontsize": 11, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "indos_no": {
        "x": 275, "y": 268, "max_width": 120, "h": 16, "fontsize": 11, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "course_name": {
        "x": 50, "y": 295, "max_width": 495, "h": 110, "fontsize": 16, "align": "center", "bold": True,
        "line_height": 20, "color": COURSE_COLOR,
    },
    "held_from": {
        "x": 125, "y": 382, "max_width": 90, "h": 18, "fontsize": 11, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "held_to": {
        "x": 250, "y": 382, "max_width": 90, "h": 18, "fontsize": 11, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "description_below": {
        "x": 48, "y": 415, "max_width": 500, "h": 145, "fontsize": 10, "align": "left", "bold": True,
        "line_height": 13, "color": (0, 0, 0),
    },
    "issue_day_month": {
        "x": 160, "y": 662, "max_width": 100, "h": 18, "fontsize": 11, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "issue_year": {
        "x": 290, "y": 662, "max_width": 55, "h": 18, "fontsize": 11, "align": "left", "bold": True,
        "color": (0, 0, 0),
    },
    "qr_label": {
        "x": 225, "y": 778, "max_width": 120, "h": 14,
        "fontsize": 9, "align": "center", "bold": True,
        "color": (0, 0, 0),
    },
    "qr_code": {
        "x": 240, "y": 685, "w": 85, "h": 85,
    },
}


def _row_get(row, key, default=None):
    try:
        if hasattr(row, "keys") and key in row.keys():
            val = row[key]
            return default if val is None else val
    except Exception:
        pass
    if isinstance(row, dict):
        return row.get(key, default)
    return default


def positions_from_db_rows(rows):
    out = {}
    for row in rows or []:
        key = _row_get(row, "field_key")
        if not key:
            continue
        x = float(_row_get(row, "x", 0) or 0)
        y = float(_row_get(row, "y", 0) or 0)
        if 0 <= x <= 1.5 and 0 <= y <= 1.5:
            ax, ay = x * A4_WIDTH, y * A4_HEIGHT
            fs = float(_row_get(row, "font_size", 0.014) or 0.014)
            fs = fs * A4_HEIGHT if fs < 1 else fs
            mw = float(_row_get(row, "width", 0.3) or 0.3)
            mw = mw * A4_WIDTH if mw <= 1.5 else mw
            vh = float(_row_get(row, "height", 0.03) or 0.03)
            vh = vh * A4_HEIGHT if vh <= 1.5 else vh
        else:
            ax, ay = x, y
            fs = float(_row_get(row, "font_size", 11) or 11)
            mw = float(_row_get(row, "width", 150) or 150)
            vh = float(_row_get(row, "height", 20) or 20)
        out[key] = {
            "x": ax, "y": ay, "max_width": mw, "h": vh, "fontsize": fs,
            "align": str(_row_get(row, "align", "left") or "left").lower(),
            "bold": bool(int(_row_get(row, "bold", 1) or 1)),
            "line_height": fs + 3,
            "color": (0, 0, 0),
        }
        if key == "qr_code":
            out[key]["w"] = mw if mw > 10 else 85
            out[key]["h"] = vh if vh > 10 else 85
        if key == "course_name":
            out[key]["color"] = COURSE_COLOR
            out[key]["bold"] = True
            out[key]["fontsize"] = float(ODS_ABS_LAYOUT["course_name"]["fontsize"])
    return out


def get_positions_for_template(template_id):
    try:
        from database.models import get_field_positions_for_template
        rows = get_field_positions_for_template(template_id)
        saved = positions_from_db_rows(rows)
        layout = {k: dict(v) for k, v in ODS_ABS_LAYOUT.items()}
        for k, v in saved.items():
            layout[k] = v
        # Always keep course name style from ODS_ABS_LAYOUT
        layout["course_name"] = dict(ODS_ABS_LAYOUT["course_name"])
        return layout
    except Exception:
        return {k: dict(v) for k, v in ODS_ABS_LAYOUT.items()}


def _template_to_pdf_bytes(template_path):
    ext = os.path.splitext(template_path)[1].lower()
    if ext == ".pdf":
        with open(template_path, "rb") as f:
            return f.read()
    if ext in (".png", ".jpg", ".jpeg"):
        doc = fitz.open()
        page = doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        page.insert_image(page.rect, filename=template_path)
        data = doc.tobytes()
        doc.close()
        return data
    if ext == ".svg":
        try:
            from weasyprint import HTML
            with open(template_path, "r", encoding="utf-8", errors="replace") as f:
                svg_content = f.read()
            html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@page {{ size: {A4_WIDTH}pt {A4_HEIGHT}pt; margin: 0; }}
html, body {{ margin: 0; padding: 0; width: {A4_WIDTH}pt; height: {A4_HEIGHT}pt; }}
svg {{ width: {A4_WIDTH}pt; height: {A4_HEIGHT}pt; display: block; }}
</style></head><body>{svg_content}</body></html>"""
            return HTML(string=html).write_pdf()
        except Exception:
            doc = fitz.open()
            doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
            data = doc.tobytes()
            doc.close()
            return data
    raise ValueError(f"Unsupported template format: {ext}")


def render_certificate_to_pdf(template_path, field_data, positions=None,
                              qr_code_path=None, output_pdf_path=None):
    if not output_pdf_path:
        raise ValueError("output_pdf_path is required")

    pdf_bytes = _template_to_pdf_bytes(template_path)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    page_w, page_h = page.rect.width, page.rect.height
    sx = page_w / A4_WIDTH
    sy = page_h / A4_HEIGHT

    layout = positions if positions else ODS_ABS_LAYOUT
    data = field_data or {}
    skip_keys = {"qr_code", "issue_date"}

    for key, pos in layout.items():
        if key in skip_keys:
            continue

        text = data.get(key, "")
        if text is None or str(text).strip() == "":
            continue
        text = str(text).strip()

        x = float(pos["x"]) * sx
        y = float(pos["y"]) * sy
        w = float(pos.get("max_width", 200)) * sx
        h = float(pos.get("h", pos.get("height", 22))) * sy

        # Course name: line-by-line (reliable size + color)
        if key == "course_name":
            base = ODS_ABS_LAYOUT["course_name"]
            fontsize = float(base.get("fontsize", 16)) * min(sx, sy)
            color = base.get("color", COURSE_COLOR)
            if not isinstance(color, (tuple, list)) or len(color) < 3:
                color = COURSE_COLOR
            line_height = float(base.get("line_height", 20)) * sy
            max_w = w

            lines = []
            for paragraph in text.replace("\r\n", "\n").split("\n"):
                words = paragraph.split() or [""]
                current = words[0]
                for word in words[1:]:
                    trial = current + " " + word
                    if fitz.get_text_length(trial, fontname="hebo", fontsize=fontsize) <= max_w:
                        current = trial
                    else:
                        lines.append(current)
                        current = word
                lines.append(current)

            for i, line in enumerate(lines):
                if not line:
                    continue
                tw = fitz.get_text_length(line, fontname="hebo", fontsize=fontsize)
                tx = x + (max_w - tw) / 2  # center
                ty = y + (i + 1) * line_height
                page.insert_text(
                    (tx, ty), line,
                    fontname="hebo", fontsize=fontsize, color=color,
                )
            continue

        fontsize = float(pos.get("fontsize", 11)) * min(sx, sy)
        bold = pos.get("bold", True)
        color = pos.get("color", (0, 0, 0))
        if not isinstance(color, (tuple, list)) or len(color) < 3:
            color = (0, 0, 0)

        align_str = str(pos.get("align", "left")).lower()
        align_code = (
            fitz.TEXT_ALIGN_CENTER if align_str == "center" else
            fitz.TEXT_ALIGN_RIGHT if align_str == "right" else
            fitz.TEXT_ALIGN_LEFT
        )
        fontname = "hebo" if bold else "helv"
        rect = fitz.Rect(x, y, x + w, y + h)

        rc = page.insert_textbox(
            rect, text, fontname=fontname, fontsize=fontsize,
            color=color, align=align_code,
        )
        if rc < 0:
            fit = fontsize - 1.5
            while fit >= 6:
                tw = fitz.get_text_length(
                    text.replace("\n", " "), fontname=fontname, fontsize=fit
                )
                if tw <= w * 1.05 or fit <= 7:
                    page.insert_textbox(
                        rect, text, fontname=fontname, fontsize=fit,
                        color=color, align=align_code,
                    )
                    break
                fit -= 1.0

    if qr_code_path and os.path.exists(qr_code_path):
        qr_pos = layout.get("qr_code", ODS_ABS_LAYOUT["qr_code"])
        qx = float(qr_pos["x"]) * sx
        qy = float(qr_pos["y"]) * sy
        qw = float(qr_pos.get("w", 85)) * sx
        qh = float(qr_pos.get("h", 85)) * sy
        try:
            page.insert_image(
                fitz.Rect(qx, qy, qx + qw, qy + qh), filename=qr_code_path
            )
        except Exception as e:
            print(f"Warning: QR insert failed: {e}")

    doc.save(output_pdf_path)
    doc.close()
    return output_pdf_path, None


def render_calibration_pdf(template_path, output_pdf_path):
    pdf_bytes = _template_to_pdf_bytes(template_path)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    page_w, page_h = page.rect.width, page.rect.height
    sx = page_w / A4_WIDTH
    sy = page_h / A4_HEIGHT

    for key, pos in ODS_ABS_LAYOUT.items():
        x = float(pos["x"]) * sx
        y = float(pos["y"]) * sy
        if key == "qr_code":
            w = float(pos.get("w", 85)) * sx
            h = float(pos.get("h", 85)) * sy
        else:
            w = float(pos.get("max_width", 150)) * sx
            h = float(pos.get("h", 20)) * sy
        rect = fitz.Rect(x, y, x + w, y + h)
        page.draw_rect(rect, color=(1, 0, 0), width=0.6)
        page.insert_text(
            (x + 2, max(8, y - 2)),
            f"{key} ({int(x)},{int(y)})",
            fontname="helv", fontsize=6, color=(1, 0, 0),
        )

    doc.save(output_pdf_path)
    doc.close()
    return output_pdf_path


PLACEHOLDER_CATALOG = [(k, k.replace("_", " ").title()) for k in ODS_ABS_LAYOUT.keys()]
DEFAULT_POSITIONS = ODS_ABS_LAYOUT
ODS_LAYOUT = ODS_ABS_LAYOUT


def render_certificate(svg_source=None, field_data=None, positions=None, qr_code_path=None, **kwargs):
    return svg_source or ""


def render_certificate_with_positions(
    svg_source=None, field_data=None, positions=None,
    qr_code_path=None, custom_positions=None, **kwargs,
):
    return svg_source or ""


def load_background_svg(file_path):
    if not file_path or not os.path.exists(file_path):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4_WIDTH}" height="{A4_HEIGHT}"></svg>',
            A4_WIDTH, A4_HEIGHT,
        )
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".svg":
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(), A4_WIDTH, A4_HEIGHT
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{A4_WIDTH}" height="{A4_HEIGHT}"></svg>',
        A4_WIDTH, A4_HEIGHT,
    )
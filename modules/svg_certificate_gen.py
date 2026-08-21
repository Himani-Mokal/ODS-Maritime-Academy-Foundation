"""
SVG certificate generation.

Templates are raw SVG files containing placeholder tokens such as
{{participant_name}}, {{event_name}}, {{certificate_id}}, {{issue_date}},
{{organization_name}}, {{course_name}}, {{description}}. These are plain text
tokens and are replaced with a simple string substitution wherever they appear
in the SVG markup (inside <text>, <tspan>, etc).

The QR code is handled specially. Template authors mark where it should go
with a placeholder element using a data-placeholder="qr_code" attribute, e.g.:

    <rect data-placeholder="qr_code" x="440" y="20" width="80" height="80" />
    <image data-placeholder="qr_code" x="440" y="20" width="80" height="80" />

That whole element is swapped for an <image> covering the same box, with the
QR code embedded as a base64 data URI.
"""

import os
import re
import base64
from flask import render_template_string

PLACEHOLDER_KEYS = [
    "participant_name",
    "event_name",
    "certificate_id",
    "issue_date",
    "organization_name",
    "course_name",
    "description",
]

_QR_PLACEHOLDER_RE = re.compile(
    r'<(rect|image)\b([^>]*?)data-placeholder=["\']qr_code["\']([^>]*?)/?\s*>',
    re.IGNORECASE | re.DOTALL,
)

_ATTR_RE_TEMPLATE = r'{name}\s*=\s*["\']([^"\']*)["\']'

_SVG_SIZE_RE = re.compile(r'<svg\b[^>]*>', re.IGNORECASE | re.DOTALL)

_SVG_OPEN_RE = re.compile(r'<svg\b([^>]*)>', re.IGNORECASE | re.DOTALL)


def _escape_xml_text(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _extract_attr(attr_string, name, default):
    match = re.search(_ATTR_RE_TEMPLATE.format(name=re.escape(name)), attr_string or "")
    return match.group(1) if match else default


def ensure_svg_namespaces(svg_source):
    """Guarantee the root <svg> has xmlns and xmlns:xlink so embedded images work."""
    def _fix_open(match):
        attrs = match.group(1) or ""
        if "xmlns=" not in attrs:
            attrs = ' xmlns="http://www.w3.org/2000/svg"' + attrs
        if "xmlns:xlink" not in attrs:
            attrs = attrs + ' xmlns:xlink="http://www.w3.org/1999/xlink"'
        return f"<svg{attrs}>"

    return _SVG_OPEN_RE.sub(_fix_open, svg_source, count=1)


def ensure_qr_placeholder(svg_source, default_size=80):
    """
    If the SVG has no data-placeholder="qr_code" element, inject one in the
    bottom-right corner so QR embedding always has a target.
    """
    if 'data-placeholder="qr_code"' in svg_source or "data-placeholder='qr_code'" in svg_source:
        return svg_source

    width, height = get_svg_dimensions(svg_source)
    qr_size = min(default_size, width * 0.12, height * 0.12)
    qr_x = max(0, width - qr_size - width * 0.04)
    qr_y = max(0, height - qr_size - height * 0.05)

    injection = (
        f'\n  <rect data-placeholder="qr_code" x="{qr_x:.1f}" y="{qr_y:.1f}" '
        f'width="{qr_size:.1f}" height="{qr_size:.1f}" fill="none" />\n'
    )

    if re.search(r"</svg\s*>", svg_source, re.IGNORECASE):
        return re.sub(r"</svg\s*>", injection + "</svg>", svg_source, count=1, flags=re.IGNORECASE)

    return svg_source + injection + "</svg>"


def render_svg_certificate(svg_source, data, qr_code_path=None):
    """
    Returns a new SVG string with placeholders substituted and the QR code
    (if a qr_code_path is given and a placeholder element exists) embedded.
    """
    svg = ensure_svg_namespaces(svg_source)
    svg = ensure_qr_placeholder(svg)

    for key in PLACEHOLDER_KEYS:
        token = "{{" + key + "}}"
        value = _escape_xml_text(data.get(key, ""))
        svg = svg.replace(token, value)

    # Common aliases some templates might use
    aliases = {
        "{{name}}": _escape_xml_text(data.get("participant_name", "")),
        "{{date}}": _escape_xml_text(data.get("issue_date", "")),
        "{{event}}": _escape_xml_text(data.get("event_name", "") or data.get("course_name", "")),
    }
    for token, value in aliases.items():
        svg = svg.replace(token, value)

    if qr_code_path and os.path.exists(qr_code_path):
        with open(qr_code_path, "rb") as f:
            qr_base64 = base64.b64encode(f.read()).decode("utf-8")
        qr_data_uri = f"data:image/png;base64,{qr_base64}"

        def _replace_qr_element(match):
            attrs = (match.group(2) or "") + (match.group(3) or "")
            x = _extract_attr(attrs, "x", "0")
            y = _extract_attr(attrs, "y", "0")
            width = _extract_attr(attrs, "width", "80")
            height = _extract_attr(attrs, "height", "80")
            return (
                f'<image x="{x}" y="{y}" width="{width}" height="{height}" '
                f'href="{qr_data_uri}" xlink:href="{qr_data_uri}" '
                f'preserveAspectRatio="xMidYMid meet" />'
            )

        svg = _QR_PLACEHOLDER_RE.sub(_replace_qr_element, svg)

    # Drop any leftover literal QR text tokens
    svg = svg.replace("{{qr_code}}", "")
    svg = svg.replace("{{QR_CODE}}", "")

    # Strip any remaining unmatched {{...}} tokens so they never appear on the certificate
    svg = re.sub(r"\{\{[^{}]+\}\}", "", svg)

    return svg


def get_svg_dimensions(svg_source, default_width=1000, default_height=700):
    """
    Best-effort extraction of the certificate's pixel size from the <svg>
    root tag, used so the generated PDF page matches the template exactly.
    """
    match = _SVG_SIZE_RE.search(svg_source)
    if not match:
        return default_width, default_height

    tag = match.group(0)
    width = _extract_attr(tag, "width", None)
    height = _extract_attr(tag, "height", None)

    def _to_px(value, fallback):
        if not value:
            return fallback
        try:
            return float(re.sub(r"[a-zA-Z%]", "", value))
        except ValueError:
            return fallback

    if width and height:
        return _to_px(width, default_width), _to_px(height, default_height)

    view_box = _extract_attr(tag, "viewBox", None)
    if view_box:
        parts = view_box.replace(",", " ").split()
        if len(parts) == 4:
            try:
                return float(parts[2]), float(parts[3])
            except ValueError:
                pass

    return default_width, default_height


_PDF_WRAPPER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    @page {
        size: {{ width }}px {{ height }}px;
        margin: 0;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; width: {{ width }}px; height: {{ height }}px; }
    .cert-wrap { width: {{ width }}px; height: {{ height }}px; overflow: hidden; }
    .cert-wrap svg {
        display: block;
        width: {{ width }}px;
        height: {{ height }}px;
    }
</style>
</head>
<body>
<div class="cert-wrap">{{ svg|safe }}</div>
</body>
</html>
"""


def svg_to_pdf(svg_string, output_path):
    """
    Renders the (already placeholder-substituted) SVG to a PDF file,
    preserving vector quality, using WeasyPrint's built-in inline-SVG support.
    """
    from weasyprint import HTML

    svg_string = ensure_svg_namespaces(svg_string)
    width, height = get_svg_dimensions(svg_string)
    # Guard against zero / tiny sizes
    width = max(width, 100)
    height = max(height, 100)

    html_string = render_template_string(
        _PDF_WRAPPER_TEMPLATE, svg=svg_string, width=width, height=height
    )
    HTML(string=html_string, base_url=".").write_pdf(output_path)
    return output_path


def pdf_to_png(pdf_path, output_path, zoom=3):
    """
    Rasterizes the first page of a PDF to a PNG at the given zoom factor
    (3x ~= 216 DPI). Requires PyMuPDF (`pip install pymupdf`).
    """
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    page = doc[0]
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix)
    pixmap.save(output_path)
    doc.close()
    return output_path


def _detect_content_bbox(img):
    """
    Detects the bounding box of the actual visible design inside the image,
    by treating the color at the top-left corner as the background and
    finding where content that differs from it starts/ends.
    """
    from PIL import ImageChops, Image

    rgb_img = img.convert("RGB")
    bg_color = rgb_img.getpixel((0, 0))
    background = Image.new("RGB", rgb_img.size, bg_color)

    diff = ImageChops.difference(rgb_img, background)
    bbox = diff.getbbox()

    return bbox if bbox else (0, 0, img.width, img.height)


def wrap_raster_image_as_svg(image_path):
    """Clean SVG background only — no placeholder text."""
    from PIL import Image
    import base64

    with Image.open(image_path) as img:
        width, height = img.size

    with open(image_path, "rb") as f:
        raw_bytes = f.read()

    ext = image_path.rsplit(".", 1)[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    data_uri = f"data:{mime};base64,{base64.b64encode(raw_bytes).decode('utf-8')}"

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        f'  <image x="0" y="0" width="{width}" height="{height}" '
        f'href="{data_uri}" xlink:href="{data_uri}" preserveAspectRatio="xMidYMid meet" />\n'
        f'</svg>'
    )
    return svg
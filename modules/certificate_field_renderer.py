"""Compatibility shim — prefer modules.certificate_renderer."""
import os
from modules.certificate_renderer import (
    render_certificate,
    render_certificate_with_positions,
    get_positions_for_template,
    load_background_svg,
    ODS_ABS_LAYOUT as ODS_LAYOUT,
    DEFAULT_POSITIONS,
    PLACEHOLDER_CATALOG,
)
from modules.svg_certificate_gen import ensure_svg_namespaces, get_svg_dimensions


def load_background_svg(file_path):
    if not file_path or not os.path.exists(file_path):
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="595.44" height="841.92"></svg>',
            595.44,
            841.92,
        )
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        svg_source = f.read()
    svg_source = ensure_svg_namespaces(svg_source)
    width, height = get_svg_dimensions(svg_source)
    return svg_source, width, height

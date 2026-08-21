"""
calibrate.py
Run from project root:
  python calibrate.py
  python calibrate.py "uploads/templates/20260805161035_ODS.svg"
"""
import sys
import os
from modules.certificate_renderer import render_calibration_pdf

DEFAULT_TEMPLATE = os.path.join("uploads", "templates", "20260804162316_ODS_Blank.svg")
DEFAULT_OUTPUT = os.path.join("generated", "calibration_grid.pdf")


def main():
    template_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TEMPLATE
    output_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT

    if not os.path.exists(template_path):
        print(f"Error: Template not found: {template_path}")
        folder = os.path.join("uploads", "templates")
        if os.path.isdir(folder):
            print("\nFiles in uploads/templates:")
            for name in sorted(os.listdir(folder)):
                print(" ", name)
        sys.exit(1)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    print(f"Rendering calibration on: {template_path}")
    render_calibration_pdf(template_path, output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
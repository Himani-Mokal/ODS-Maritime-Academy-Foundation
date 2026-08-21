import qrcode


def generate_qr_code(data, output_path):
    """
    Create a QR code from plain text (or URL) and save as PNG.
    Uses fit=True so longer student-detail text still fits.
    """
    qr = qrcode.QRCode(
        version=None,  # auto size for longer text
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)
    return output_path
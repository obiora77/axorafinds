"""Processing for uploaded listing photos."""
from io import BytesIO

from PIL import Image, ImageOps

MAX_SIDE = 1600  # longest edge in pixels; plenty for a listing page, small enough to store cheaply
QUALITY = 82
CONTENT_TYPE = 'image/webp'


def compress_image(raw: bytes) -> tuple[bytes, str]:
    """Returns (bytes, content_type): upright, at most 1600px on the long side, as WebP.

    Re-encoding also strips EXIF data such as the GPS location a phone camera records.
    """
    with Image.open(BytesIO(raw)) as source:
        image = ImageOps.exif_transpose(source)
        image.thumbnail((MAX_SIDE, MAX_SIDE))
        has_alpha = 'A' in image.getbands() or image.info.get('transparency') is not None
        image = image.convert('RGBA' if has_alpha else 'RGB')
        out = BytesIO()
        image.save(out, format='WEBP', quality=QUALITY, method=4)
    return out.getvalue(), CONTENT_TYPE

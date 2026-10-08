import io
import uuid
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

try:
    from rembg import remove as rembg_remove  # optional AI feature
    HAS_REMBG = True
except Exception:
    HAS_REMBG = False

BASE = Path(__file__).parent
UPLOADS = BASE / "uploads"
UPLOADS.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
MAX_SIDE = 2000  # downscale huge images for speed


def load(image_id):
    path = UPLOADS / f"{Path(image_id).name}.png"
    if not path.exists():
        return None
    return Image.open(path).convert("RGBA")


def auto_enhance(img):
    """Simple 'AI-style' auto fix: stretch histogram + mild saturation/sharpness."""
    rgb = ImageOps.autocontrast(img.convert("RGB"), cutoff=1)
    rgb = ImageEnhance.Color(rgb).enhance(1.15)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.3)
    out = rgb.convert("RGBA")
    out.putalpha(img.split()[-1])
    return out


def sepia(img):
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    m = np.array([[0.393, 0.769, 0.189],
                  [0.349, 0.686, 0.168],
                  [0.272, 0.534, 0.131]])
    out = np.clip(arr @ m.T, 0, 255).astype(np.uint8)
    res = Image.fromarray(out).convert("RGBA")
    res.putalpha(img.split()[-1])
    return res


def apply_edits(img, p):
    alpha = img.split()[-1]

    # AI: background removal (optional dependency)
    if p.get("remove_bg") and HAS_REMBG:
        img = rembg_remove(img)
        alpha = img.split()[-1]

    if p.get("auto_enhance"):
        img = auto_enhance(img)

    # Geometry
    rot = int(p.get("rotate", 0)) % 360
    if rot:
        img = img.rotate(-rot, expand=True)
    if p.get("flip_h"):
        img = ImageOps.mirror(img)
    if p.get("flip_v"):
        img = ImageOps.flip(img)

    crop = p.get("crop")  # {x,y,w,h} in percentages 0-100
    if crop:
        w, h = img.size
        x0 = int(w * crop["x"] / 100); y0 = int(h * crop["y"] / 100)
        x1 = x0 + int(w * crop["w"] / 100); y1 = y0 + int(h * crop["h"] / 100)
        if x1 > x0 and y1 > y0:
            img = img.crop((x0, y0, min(x1, w), min(y1, h)))

    scale = float(p.get("scale", 100)) / 100
    if scale != 1 and scale > 0:
        w, h = img.size
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)

    # Color adjustments (work on RGB, keep alpha)
    alpha = img.split()[-1]
    rgb = img.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(float(p.get("brightness", 100)) / 100)
    rgb = ImageEnhance.Contrast(rgb).enhance(float(p.get("contrast", 100)) / 100)
    rgb = ImageEnhance.Color(rgb).enhance(float(p.get("saturation", 100)) / 100)
    rgb = ImageEnhance.Sharpness(rgb).enhance(float(p.get("sharpness", 100)) / 100)

    blur = float(p.get("blur", 0))
    if blur > 0:
        rgb = rgb.filter(ImageFilter.GaussianBlur(blur))

    flt = p.get("filter", "none")
    if flt == "grayscale":
        rgb = ImageOps.grayscale(rgb).convert("RGB")
    elif flt == "sepia":
        rgb = sepia(rgb).convert("RGB")
    elif flt == "invert":
        rgb = ImageOps.invert(rgb)
    elif flt == "edges":
        rgb = rgb.filter(ImageFilter.FIND_EDGES)
    elif flt == "emboss":
        rgb = rgb.filter(ImageFilter.EMBOSS)
    elif flt == "sketch":
        gray = ImageOps.grayscale(rgb)
        inv = ImageOps.invert(gray).filter(ImageFilter.GaussianBlur(8))
        g = np.array(gray, dtype=np.float32)
        b = np.array(inv, dtype=np.float32)
        sk = np.clip(g * 255 / (255 - b + 1), 0, 255).astype(np.uint8)
        rgb = Image.fromarray(sk).convert("RGB")

    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


@app.route("/")
def index():
    return render_template("index.html", has_rembg=HAS_REMBG)


@app.route("/api/upload", methods=["POST"])
def upload():
    f = request.files.get("image")
    if not f:
        return jsonify(error="No file uploaded"), 400
    try:
        img = Image.open(f.stream)
        img = ImageOps.exif_transpose(img).convert("RGBA")
    except Exception:
        return jsonify(error="Invalid image file"), 400
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    image_id = uuid.uuid4().hex
    img.save(UPLOADS / f"{image_id}.png")
    return jsonify(id=image_id, width=img.width, height=img.height)


@app.route("/api/process", methods=["POST"])
def process():
    data = request.get_json(force=True)
    img = load(data.get("id", ""))
    if img is None:
        return jsonify(error="Image not found"), 404
    out = apply_edits(img, data.get("params", {}))
    buf = io.BytesIO()
    fmt = data.get("format", "png").lower()
    if fmt in ("jpg", "jpeg"):
        bg = Image.new("RGB", out.size, (255, 255, 255))
        bg.paste(out, mask=out.split()[-1])
        bg.save(buf, "JPEG", quality=92)
        mime = "image/jpeg"
    else:
        out.save(buf, "PNG")
        mime = "image/png"
    buf.seek(0)
    return send_file(buf, mimetype=mime)


if __name__ == "__main__":
    app.run(debug=False)

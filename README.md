# AI Image Editor

A Flask + Pillow web app for editing images in the browser with live preview.

## Features
- Upload via click or drag & drop
- Adjust brightness, contrast, saturation, sharpness, blur, scale
- Filters: grayscale, sepia, invert, edges, emboss, pencil sketch
- Rotate, flip, percentage-based crop
- AI tools: auto enhance (histogram stretch + tone tweaks) and
  optional background removal (via `rembg`)
- Download as PNG or JPEG

## Run
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Enable background removal
Uncomment `rembg` and `onnxruntime` in `requirements.txt`, then
`pip install -r requirements.txt` (first run downloads a model).

## Structure
```
app.py            Flask routes + image processing
templates/        index.html
static/           style.css, script.js
uploads/          temporary originals (git-ignored)
```

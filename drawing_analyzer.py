"""
MechForge AI V2 - Drawing Analyzer
Extracts useful DFM parameters from dimensioned PDF/image drawings.

PDF: uses pypdf text extraction.
PNG/JPG: uses pytesseract if installed (Tesseract itself must also be installed).
The analyzer is deliberately conservative: it only returns values that it can
find in the drawing text; otherwise the app keeps the manual/default value.
"""

import re
from pathlib import Path

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None


def extract_pdf_text(file_bytes: bytes) -> str:
    if PdfReader is None:
        return ""
    try:
        import io
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                pages.append("")
        return "\n".join(pages)
    except Exception:
        return ""


def extract_image_text(file_bytes: bytes) -> str:
    if Image is None or pytesseract is None:
        return ""
    try:
        import io
        image = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(image)
    except Exception:
        return ""


def extract_drawing_text(file_name: str, file_bytes: bytes) -> tuple[str, str]:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(file_bytes), "PDF text extraction"
    if suffix in {".png", ".jpg", ".jpeg"}:
        return extract_image_text(file_bytes), "OCR (Tesseract)"
    return "", "unsupported file type"


def _num(pattern: str, text: str, flags=re.I):
    m = re.search(pattern, text, flags)
    if not m:
        return None
    try:
        return float(m.group(1))
    except (ValueError, TypeError):
        return None


def _all_numbers(pattern: str, text: str, flags=re.I):
    out = []
    for m in re.finditer(pattern, text, flags):
        try:
            out.append(float(m.group(1)))
        except (ValueError, TypeError):
            pass
    return out


def analyze_drawing_text(text: str) -> dict:
    """Return only parameters confidently detected from drawing text."""
    raw = text or ""
    t = re.sub(r"[ \t]+", " ", raw)
    t = t.replace("Ø", " DIA ").replace("⌀", " DIA ")
    result = {
        "detected": {},
        "features": [],
        "notes": [],
        "raw_text": raw,
    }

    # Material / process notes
    material_patterns = [
        r"\bMaterial\s*[:\-]\s*([A-Za-z0-9 ._-]+?)(?=\s+(?:Process|Minimum|Deepest|Narrowest|General|Surface|Drawing|Rev|Scale)|\n|$)",
        r"\b(ALUMINIUM\s+6061|ALUMINUM\s+6061|ALUMINIUM\s+7075|ALUMINUM\s+7075|STAINLESS\s+STEEL|MILD\s+STEEL|TITANIUM|BRASS|COPPER)\b",
    ]
    for p in material_patterns:
        m = re.search(p, raw, re.I)
        if m:
            material = m.group(1).strip()
            material = re.sub(r"\s+", " ", material)
            aliases = {
                "ALUMINUM 6061": "Aluminium 6061",
                "ALUMINIUM 6061": "Aluminium 6061",
                "ALUMINUM 7075": "Aluminium 7075",
                "ALUMINIUM 7075": "Aluminium 7075",
            }
            result["detected"]["material"] = aliases.get(material.upper(), material.title())
            break

    m = re.search(r"\bProcess\s*[:\-]\s*([A-Za-z ]+)", raw, re.I)
    if m:
        result["detected"]["process"] = m.group(1).strip().title()

    # Explicit DFM notes are more reliable than guessing from arbitrary dimensions.
    pairs = [
        ("wall", r"(?:Minimum\s+wall\s+thickness|Min\.?\s*wall)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*mm"),
        ("pocket_depth", r"(?:Deepest\s+pocket|Pocket\s+depth)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*mm"),
        ("pocket_width", r"(?:Narrowest\s+pocket\s+width|Pocket\s+width)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*mm"),
        ("hole_depth", r"(?:Deepest\s+hole|Hole\s+depth)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*mm"),
    ]
    for key, p in pairs:
        value = _num(p, raw)
        if value is not None:
            result["detected"][key] = value

    # Radii: use the smallest explicit radius because it is the limiting DFM feature.
    radii = _all_numbers(r"\bR\s*([0-9]+(?:\.[0-9]+)?)\s*mm?\b", raw)
    if radii:
        result["detected"]["radius"] = min(radii)
        result["features"].append(f"Radii detected: {', '.join(f'R{x:g}' for x in sorted(set(radii)))} mm")

    # Holes: support Ø10, DIA 10, 2X Ø10 THRU, etc.
    holes = _all_numbers(r"(?:\bDIA\s*|\bØ\s*|\b⌀\s*)([0-9]+(?:\.[0-9]+)?)\s*mm?\b", raw)
    if holes:
        result["detected"]["hole_dia"] = min(holes)
        result["features"].append(f"Hole diameters detected: {', '.join(f'Ø{x:g}' for x in sorted(set(holes)))} mm")
        if re.search(r"(?:THRU|THROUGH)", raw, re.I):
            result["features"].append("Through-hole feature detected")

    # Tolerance: ±0.05, +0.05/-0.02, GENERAL TOL: ±0.05
    tol = _num(r"±\s*([0-9]+(?:\.[0-9]+)?)\s*mm?", raw)
    if tol is None:
        tol = _num(r"(?:GENERAL\s+TOL(?:ERANCE)?|TOL(?:ERANCE)?)\s*[:=]?\s*±?\s*([0-9]+(?:\.[0-9]+)?)\s*mm?", raw)
    if tol is not None:
        result["detected"]["tolerance"] = tol

    # Surface finish: Ra 3.2 µm / Ra 0.8
    ra = _num(r"\bRa\s*([0-9]+(?:\.[0-9]+)?)\s*(?:µm|um|μm)?", raw)
    if ra is not None:
        result["detected"]["surface_ra"] = ra

    # Overall dimensions: collect standalone dimension values, useful for display.
    dims = _all_numbers(r"(?<![A-Za-z0-9])([0-9]+(?:\.[0-9]+)?)\s*mm\b", raw)
    if dims:
        unique = sorted(set(dims))
        result["detected"]["dimensions"] = unique[:30]
        result["features"].append(f"{len(unique)} unique linear dimensions detected")

    # Look for common manufacturing features.
    feature_checks = [
        (r"\bSLOT\b", "Slot detected"),
        (r"\bTHREAD(?:ED|ING)?\b|\bM\d+\b", "Thread feature detected"),
        (r"\bCHAMFER\b|\bC\s*[0-9]", "Chamfer feature detected"),
        (r"\bPOCKET\b", "Pocket feature detected"),
        (r"\bBLIND\b", "Blind feature detected"),
    ]
    for p, label in feature_checks:
        if re.search(p, raw, re.I):
            result["features"].append(label)

    # Normalize process if the drawing has an exact known process.
    process = result["detected"].get("process")
    known = {
        "cnc milling": "CNC Milling",
        "cnc turning": "CNC Turning",
        "drilling": "Drilling",
        "grinding": "Grinding",
        "sheet metal": "Sheet Metal",
        "laser cutting": "Laser Cutting",
        "waterjet cutting": "Waterjet Cutting",
        "casting": "Casting",
        "forging": "Forging",
        "injection molding": "Injection Molding",
        "3d printing": "3D Printing",
        "welding": "Welding",
    }
    if process:
        result["detected"]["process"] = known.get(process.lower(), process)

    if result["detected"]:
        result["notes"].append("Values shown as detected were extracted from the uploaded drawing text.")
    else:
        result["notes"].append("No reliable DFM dimensions were extracted. Enter/verify dimensions manually.")

    return result

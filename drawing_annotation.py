"""MechForge AI — Drawing Issue Annotation V2.

Creates an annotated copy of an uploaded drawing using the deterministic DFM
findings. Because text/PDF extraction does not provide trustworthy feature
coordinates, this version deliberately uses a professional side-panel callout
instead of inventing marker positions on the geometry.
"""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


def _font(size=20, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _wrap(text, width_chars):
    words = str(text or "").split()
    lines, current = [], ""
    for word in words:
        trial = word if not current else current + " " + word
        if len(trial) <= width_chars:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _relevant_issues(issues):
    return [x for x in (issues or []) if x.get("priority") in {"HIGH", "MEDIUM"}]


def _priority_colors(priority):
    if priority == "HIGH":
        return (255, 235, 235), (190, 55, 55), (125, 25, 25)
    return (255, 247, 222), (205, 145, 35), (105, 75, 15)


def annotate_image(file_bytes, issues):
    image = Image.open(BytesIO(file_bytes)).convert("RGB")
    scale = max(1.0, 1800 / max(image.width, 1))
    if scale != 1.0:
        image = image.resize((int(image.width * scale), int(image.height * scale)))

    panel_w = max(520, int(image.width * 0.38))
    output = Image.new("RGB", (image.width + panel_w, image.height), "white")
    output.paste(image, (0, 0))
    draw = ImageDraw.Draw(output)

    title_font = _font(32, True)
    section_font = _font(23, True)
    body_font = _font(18)
    small_font = _font(15)

    x0 = image.width + 28
    y = 28
    draw.text((x0, y), "MechForge AI", font=title_font, fill=(25, 35, 45))
    y += 46
    draw.text((x0, y), "Drawing Issue Annotation", font=section_font, fill=(25, 35, 45))
    y += 38
    draw.text((x0, y), "Rule-based DFM review", font=small_font, fill=(90, 100, 110))
    y += 34

    relevant = _relevant_issues(issues)
    if not relevant:
        draw.rounded_rectangle(
            (x0 - 12, y, output.width - 20, y + 112),
            radius=12,
            fill=(235, 248, 239),
            outline=(100, 170, 115),
            width=2,
        )
        draw.text((x0, y + 16), "✓ No HIGH/MEDIUM issues", font=section_font, fill=(40, 100, 55))
        draw.text((x0, y + 54), "Current DFM rules found no annotation targets.", font=small_font, fill=(60, 75, 65))
        draw.text((x0, y + 76), "GOOD findings may still be present in the DFM report.", font=small_font, fill=(60, 75, 65))
    else:
        draw.text((x0, y), f"{len(relevant)} issue(s) requiring review", font=body_font, fill=(70, 75, 82))
        y += 38
        for idx, issue in enumerate(relevant, 1):
            priority = issue.get("priority", "MEDIUM")
            fill, outline, text_color = _priority_colors(priority)
            title = f"{idx}. {priority} — {issue.get('title', 'DFM issue')}"

            lines = []
            for label, key in [
                ("Observed", "observed"),
                ("Problem", "problem"),
                ("Recommendation", "recommendation"),
                ("Benefit", "benefit"),
            ]:
                lines.append((label, _wrap(issue.get(key, ""), max(34, int(panel_w / 12)))))

            card_h = 58
            for _, wrapped in lines:
                card_h += 22 + min(len(wrapped), 3) * 18 + 6
            card_h = min(max(card_h, 220), 330)

            if y + card_h > output.height - 95:
                draw.text((x0, y), "Additional issues are listed in the DFM report.", font=small_font, fill=(95, 100, 105))
                break

            draw.rounded_rectangle(
                (x0 - 12, y, output.width - 20, y + card_h),
                radius=12,
                fill=fill,
                outline=outline,
                width=2,
            )
            draw.text((x0, y + 12), title, font=section_font, fill=text_color)
            yy = y + 50
            for label, wrapped in lines:
                draw.text((x0, yy), f"{label}:", font=body_font, fill=(45, 50, 55))
                yy += 23
                for line in wrapped[:3]:
                    draw.text((x0, yy), line, font=small_font, fill=(75, 80, 85))
                    yy += 18
                yy += 5
            y += card_h + 16

    draw.text(
        (x0, output.height - 58),
        "Coordinates are not inferred from text/OCR.",
        font=small_font,
        fill=(100, 105, 110),
    )
    draw.text(
        (x0, output.height - 36),
        "Verify findings against the original drawing before manufacture.",
        font=small_font,
        fill=(100, 105, 110),
    )

    out = BytesIO()
    output.save(out, format="PNG", optimize=True)
    return out.getvalue(), "png"


def _draw_pdf_wrapped(c, text, x, y, width_chars, font="Helvetica", size=7.2, leading=9):
    c.setFont(font, size)
    for line in _wrap(text, width_chars):
        c.drawString(x, y, line[:60])
        y -= leading
    return y


def _make_pdf_panel(width, height, issues):
    panel = BytesIO()
    c = canvas.Canvas(panel, pagesize=(width, height))
    panel_w = 290
    panel_x = width - panel_w

    c.setFillColorRGB(0.965, 0.975, 0.985)
    c.rect(panel_x, 0, panel_w, height, fill=1, stroke=0)

    c.setFillColorRGB(0.10, 0.14, 0.18)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(panel_x + 16, height - 28, "MechForge AI")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(panel_x + 16, height - 46, "Drawing Issue Annotation")
    c.setFont("Helvetica", 7.5)
    c.setFillColorRGB(0.38, 0.42, 0.46)
    c.drawString(panel_x + 16, height - 60, "Rule-based DFM review")

    relevant = _relevant_issues(issues)
    y = height - 82
    if not relevant:
        c.setFillColorRGB(0.85, 0.95, 0.88)
        c.roundRect(panel_x + 12, y - 68, panel_w - 24, 68, 8, fill=1, stroke=0)
        c.setFillColorRGB(0.15, 0.40, 0.22)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(panel_x + 22, y - 24, "✓ No HIGH/MEDIUM issues")
        c.setFont("Helvetica", 7.5)
        c.drawString(panel_x + 22, y - 39, "Current DFM rules found no")
        c.drawString(panel_x + 22, y - 50, "annotation targets.")
    else:
        c.setFillColorRGB(0.28, 0.31, 0.35)
        c.setFont("Helvetica", 8)
        c.drawString(panel_x + 16, y, f"{len(relevant)} issue(s) requiring review")
        y -= 16

        for idx, issue in enumerate(relevant, 1):
            priority = issue.get("priority", "MEDIUM")
            if priority == "HIGH":
                c.setFillColorRGB(1.0, 0.91, 0.91)
            else:
                c.setFillColorRGB(1.0, 0.96, 0.84)

            card_h = 170
            if y - card_h < 48:
                break
            c.roundRect(panel_x + 10, y - card_h, panel_w - 20, card_h, 7, fill=1, stroke=0)

            c.setFillColorRGB(0.15, 0.17, 0.20)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawString(panel_x + 18, y - 18, f"{idx}. {priority} — {issue.get('title', 'DFM issue')}"[:45])

            yy = y - 35
            for label, key in [
                ("Observed", "observed"),
                ("Problem", "problem"),
                ("Recommendation", "recommendation"),
                ("Benefit", "benefit"),
            ]:
                c.setFillColorRGB(0.20, 0.22, 0.25)
                c.setFont("Helvetica-Bold", 7)
                c.drawString(panel_x + 18, yy, f"{label}:")
                yy -= 10
                c.setFillColorRGB(0.30, 0.32, 0.35)
                yy = _draw_pdf_wrapped(c, issue.get(key, ""), panel_x + 18, yy, 42, size=6.7, leading=8)
                yy -= 4
            y -= card_h + 10

    c.setFillColorRGB(0.45, 0.48, 0.52)
    c.setFont("Helvetica", 6.2)
    c.drawString(panel_x + 14, 26, "Coordinates are not inferred from text/OCR.")
    c.drawString(panel_x + 14, 16, "Verify findings before manufacture.")
    c.save()
    panel.seek(0)
    return PdfReader(panel).pages[0]


def annotate_pdf(file_bytes, issues):
    reader = PdfReader(BytesIO(file_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        old_w = float(page.mediabox.width)
        old_h = float(page.mediabox.height)
        panel_w = 290
        new_page = writer.add_blank_page(width=old_w + panel_w, height=old_h)
        new_page.merge_translated_page(page, 0, 0)
        panel = _make_pdf_panel(old_w + panel_w, old_h, issues)
        new_page.merge_page(panel)

    out = BytesIO()
    writer.write(out)
    return out.getvalue(), "pdf"


def annotate_drawing(filename, file_bytes, issues):
    ext = Path(filename).suffix.lower()
    if ext in {".png", ".jpg", ".jpeg"}:
        return annotate_image(file_bytes, issues)
    if ext == ".pdf":
        return annotate_pdf(file_bytes, issues)
    raise ValueError("Unsupported drawing format for annotation.")

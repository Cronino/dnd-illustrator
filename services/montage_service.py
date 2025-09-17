from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from models.entities import Scene


class MontageService:
    def __init__(self, output_dir: str | Path = "data") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_pdf(self, campaign_name: str, scenes: List[Scene], filepath: Optional[str] = None) -> str:
        safe_name = campaign_name.replace(" ", "_")
        pdf_path = Path(filepath) if filepath else (self.output_dir / f"{safe_name}_montage.pdf")
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        width, height = letter

        for scene in scenes:
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, scene.title)
            y_cursor = height - 80

            if scene.image_path and Path(scene.image_path).exists():
                try:
                    img = ImageReader(scene.image_path)
                    img_width, img_height = img.getSize()
                    max_w, max_h = width - 100, height - 200
                    scale = min(max_w / img_width, max_h / img_height)
                    draw_w, draw_h = img_width * scale, img_height * scale
                    c.drawImage(img, 50, y_cursor - draw_h, draw_w, draw_h, preserveAspectRatio=True, mask='auto')
                    y_cursor = y_cursor - draw_h - 20
                except Exception:
                    pass

            c.setFont("Helvetica", 12)
            caption = scene.caption or ""
            # Simple wrap at ~90 chars
            lines = []
            line = ""
            for word in caption.split():
                if len(line) + 1 + len(word) > 90:
                    lines.append(line)
                    line = word
                else:
                    line = f"{line} {word}".strip()
            if line:
                lines.append(line)
            for li in lines:
                c.drawString(50, y_cursor, li)
                y_cursor -= 16

            c.showPage()

        c.save()
        return str(pdf_path)



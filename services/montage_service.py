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

    def export_mp4(self, campaign_name: str, scenes: List[Scene], seconds_per_scene: float = 4.0, fps: int = 30, filepath: Optional[str] = None) -> str:
        """Create a simple MP4 with slow pan/zoom (Ken Burns-style) using moviepy.

        Requires moviepy to be installed.
        """
        try:
            # Fix PIL.ANTIALIAS compatibility issue with newer Pillow versions
            import PIL.Image
            if not hasattr(PIL.Image, 'ANTIALIAS'):
                PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
            
            from moviepy.editor import ImageClip, concatenate_videoclips
        except ImportError:
            raise ImportError("MoviePy is not properly installed. Try: uv add moviepy && uv sync")

        safe_name = campaign_name.replace(" ", "_")
        mp4_path = Path(filepath) if filepath else (self.output_dir / f"{safe_name}_montage.mp4")

        clips = []
        valid_scenes = []
        
        for sc in scenes:
            if not sc.image_path:
                continue
            
            # Check if image exists at the stored path
            image_path = Path(sc.image_path)
            if not image_path.exists():
                # Try to find the image in the old flat structure
                old_path = self.images_dir / f"scene-{sc.id}.png"
                if old_path.exists():
                    image_path = old_path
                else:
                    continue
                
            try:
                clip = ImageClip(str(image_path), duration=seconds_per_scene)
                # Add Ken Burns effect (slow zoom)
                zoomed = clip.resize(lambda t: 1.0 + 0.05 * (t / max(seconds_per_scene, 0.01)))
                clips.append(zoomed)
                valid_scenes.append(sc.title)
            except Exception as e:
                continue

        if not clips:
            scene_info = []
            for sc in scenes:
                exists = False
                if sc.image_path:
                    exists = Path(sc.image_path).exists()
                    if not exists:
                        # Check old location
                        old_path = self.images_dir / f"scene-{sc.id}.png"
                        exists = old_path.exists()
                scene_info.append(f"'{sc.title}': image_path={sc.image_path}, exists={exists}")
            raise ValueError(f"No valid scenes with images found. Scene details:\n" + "\n".join(scene_info))

        try:
            final = concatenate_videoclips(clips, method="compose")
            final.write_videofile(str(mp4_path), fps=fps, codec="libx264", audio=False, verbose=False, logger=None)
            return str(mp4_path)
        except Exception as e:
            raise RuntimeError(f"Failed to create MP4: {e}")



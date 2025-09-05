#!/usr/bin/env python3
"""
Adapted from your original plate_maker.py for Streamlit UI
Fixed to use catalog name instead of filename
"""

import io
from PIL import Image, ImageDraw, ImageFont
import rembg
from pathlib import Path

class PlateMaker:
    def __init__(self):
        # Your exact original configuration
        self.FRAME_W, self.FRAME_H = 5000, 4000
        self.SIDE_PAD = 40
        self.TOP_PAD = 40
        self.BOTTOM_PAD = 40
        self.BANNER_PAD_Y = 60
        self.MAX_FONT_SIZE = 180
        self.MIN_FONT_SIZE = 40
        self.TEXT_COLOR = (0, 0, 0)
        self.FONT_PATH = "fonts/NotoSerifDisplay-Italic-VariableFont_wdth,wght.ttf"
        self.FALLBACK_FONTS = ("DejaVuSans-Bold.ttf", "arial.ttf")
        self.LOGO_PATH = "logo/Shobha Emboss.png"
    
    def process_image(self, image_file, catalog, design_number, status_callback=None):
        """
        Main processing method - FIXED to use catalog name
        """
        if status_callback:
            status_callback("📤 Reading image...")
        
        # Convert uploaded file to PIL Image for processing
        if hasattr(image_file, 'read'):
            img_bytes = image_file.read()
        else:
            img_bytes = image_file
        
        # FIXED: Always use catalog name instead of filename
        name = catalog
        
        filename = image_file.name if hasattr(image_file, 'name') else 'uploaded_image'
        print(f"→ Processing: {filename} with catalog name: {name}")
        
        if status_callback:
            status_callback("🎭 Removing background...")
        
        # 1. Remove BG & trim transparency (your original methods)
        fg = self.remove_bg_from_bytes(img_bytes)
        fg = self.trim_transparent(fg)
        
        if status_callback:
            status_callback("📏 Resizing image...")
        
        # 2. Downsize into fixed window (your original method)
        fg = self.downsize(fg, self.FRAME_W, self.FRAME_H)
        
        if status_callback:
            status_callback("🏷️ Adding logo overlay...")
        
        # 3. Overlay logo on the saree itself (your original method)
        fg_canvas = Image.new("RGBA", fg.size, (0,0,0,0))
        fg_canvas.paste(fg, (0,0), fg)
        fg_canvas = self.add_logo_overlay(fg_canvas, (0,0), (fg.width, fg.height))
        fg = fg_canvas
        
        if status_callback:
            status_callback("✏️ Creating banner...")
        
        # 4. Prepare banner text using catalog name
        banner_text = self.make_banner_text(name, design_number)
        font = self.best_font(banner_text, self.FRAME_W)
        tw, th = self.text_wh(banner_text, font)
        banner_h = th + 2 * self.BANNER_PAD_Y
        
        if status_callback:
            status_callback("🎨 Composing final image...")
        
        # 5. Create final white canvas & draw banner (your original method)
        cv = self.make_canvas(banner_h)
        draw = ImageDraw.Draw(cv)
        bx = self.SIDE_PAD + (self.FRAME_W - tw)//2
        by = self.TOP_PAD + (banner_h - th)//2
        draw.text((bx, by), banner_text, font=font, fill=self.TEXT_COLOR)
        
        # 6. Paste the saree+logo onto the canvas (your original method)
        sx = self.SIDE_PAD + (self.FRAME_W - fg.width)//2
        sy = self.TOP_PAD + banner_h + (self.FRAME_H - fg.height)//2
        cv.paste(fg, (sx, sy), fg)
        
        if status_callback:
            status_callback("✅ Image processing complete!")
        
        # 7. Return final RGB image (your original quality)
        return cv.convert("RGB")
    
    # Your original methods preserved exactly
    def remove_bg_from_bytes(self, img_bytes):
        """Your original remove_bg adapted for bytes input"""
        out_bytes = rembg.remove(img_bytes)
        return Image.open(io.BytesIO(out_bytes)).convert("RGBA")
    
    def trim_transparent(self, img):
        """Your exact original method"""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        bbox = img.getbbox()
        return img.crop(bbox) if bbox else img
    
    def downsize(self, img, box_w, box_h):
        """Your exact original method"""
        if img.width <= box_w and img.height <= box_h:
            return img
        scale = min(box_w / img.width, box_h / img.height)
        return img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.Resampling.LANCZOS
        )
    
    def make_canvas(self, banner_h):
        """Your exact original method"""
        w = self.FRAME_W + 2 * self.SIDE_PAD
        h = self.TOP_PAD + banner_h + self.FRAME_H + self.BOTTOM_PAD
        return Image.new("RGB", (w, h), "white")
    
    def add_logo_overlay(self, canvas, fg_pos, fg_size, 
                        size_ratio=0.20, opacity=0.31, margin=100):
        """Your exact original logo overlay method"""
        canvas = canvas.convert("RGBA")
        
        # Load & resize logo
        logo = Image.open(self.LOGO_PATH).convert("RGBA")
        target_w = int(fg_size[0] * size_ratio)
        scale = target_w / logo.width
        logo = logo.resize(
            (target_w, int(logo.height * scale)),
            Image.Resampling.LANCZOS
        )
        
        # Fade alpha
        alpha = logo.split()[3].point(lambda p: int(p * opacity))
        logo.putalpha(alpha)
        
        # Compute position within saree region
        sx, sy = fg_pos
        fw, fh = fg_size
        lx = sx + fw - logo.width - margin
        ly = sy + fh - logo.height - margin
        
        canvas.paste(logo, (lx, ly), logo)
        return canvas
    
    def make_banner_text(self, name, design):
        """Your exact original banner format"""
        return f"{name} 6.30 D.No {design}"
    
    def load_font(self, pts):
        """Your exact original font loading with variable font support"""
        try:
            return ImageFont.truetype(
                self.FONT_PATH, pts,
                layout_engine=ImageFont.LAYOUT_RAQM,
                font_variation={"wght":800,"ital":1}
            )
        except Exception:
            try:
                return ImageFont.truetype(self.FONT_PATH, pts)
            except Exception:
                for fb in self.FALLBACK_FONTS:
                    try:
                        return ImageFont.truetype(fb, pts)
                    except OSError:
                        continue
                return ImageFont.load_default()
    
    def text_wh(self, txt, font):
        """Your exact original method"""
        x0, y0, x1, y1 = font.getbbox(txt)
        return x1 - x0, y1 - y0
    
    def best_font(self, txt, max_w):
        """Your exact original auto-sizing font method"""
        for size in range(self.MAX_FONT_SIZE, self.MIN_FONT_SIZE - 1, -2):
            f = self.load_font(size)
            if self.text_wh(txt, f)[0] <= max_w:
                return f
        return self.load_font(self.MIN_FONT_SIZE)

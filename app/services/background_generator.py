import math
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image, ImageDraw, ImageFilter
from app.services.media_probe import get_ffmpeg_binary
from app.services.theme_catalog import get_theme_catalog, get_theme, public_theme_payload, get_moods


class BackgroundGenerator:
    """
    Procedural Canvas Background Generator for LyricSync Studio.
    Provides aesthetic, modern music studio templates for karaoke and lyric videos.
    Supports multiple aspect ratios: 16:9, 9:16, 1:1, 4:5.
    """

    ASPECT_RATIOS = {
        "16:9": (1920, 1080),
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
        "4:5": (1080, 1350),
    }

    # Kept for backward-compatible imports/tests; live list comes from theme_catalog.
    TEMPLATES = get_theme_catalog()

    @classmethod
    def get_templates(cls):
        return [public_theme_payload(t) for t in get_theme_catalog()]

    @classmethod
    def get_moods(cls):
        return get_moods()

    @classmethod
    def get_dimensions(cls, aspect_ratio: str = "16:9") -> tuple[int, int]:
        return cls.ASPECT_RATIOS.get(aspect_ratio, (1920, 1080))

    @staticmethod
    def _hex_rgb(value: str, fallback=(20, 20, 28)) -> Tuple[int, int, int]:
        text = (value or "").lstrip("#")
        if len(text) == 3:
            text = "".join(ch * 2 for ch in text)
        if len(text) != 6:
            return fallback
        try:
            return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
        except ValueError:
            return fallback

    @classmethod
    def generate_pattern_image(cls, pattern_type: str = "burgundy_studio", width: int = 1920, height: int = 1080) -> Image.Image:
        """
        Generates a canvas pattern image based on the selected template and dimensions.
        """
        pattern_type = pattern_type.lower().strip() if pattern_type else "burgundy_studio"

        # Placeholder thumb for the AI lyric scene card (real image is generated per project).
        if pattern_type == "ai_lyric_scene":
            return cls._render_ai_lyric_placeholder(width, height)

        # Prefer catalog-driven parametric looks for the expanded library.
        theme = get_theme(pattern_type)
        if theme and (theme.get("asset") or theme.get("style") == "photo"):
            return cls._spec_photo(width, height, theme)
        if theme and theme.get("style"):
            return cls._render_from_spec(width, height, theme)

        legacy = {
            "burgundy_studio": cls._render_burgundy_studio,
            "deep_nebula": cls._render_deep_nebula,
            "retrowave_sunset": cls._render_retrowave_sunset,
            "midnight_acoustic": cls._render_midnight_acoustic,
            "abstract_aurora": cls._render_abstract_aurora,
            "minimal_dark": cls._render_minimal_dark,
            "cyberpunk_neon": cls._render_cyberpunk_neon,
            "golden_hour": cls._render_golden_hour,
            "velvet_lounge": cls._render_velvet_lounge,
            "lofi_chill": cls._render_lofi_chill,
        }
        gen_func = legacy.get(pattern_type, cls._render_burgundy_studio)
        return gen_func(width, height)

    @classmethod
    def _asset_path(cls, asset: str) -> Path:
        from config import BASE_DIR
        return Path(BASE_DIR) / "static" / asset

    @classmethod
    def _cover_crop(cls, img: Image.Image, width: int, height: int) -> Image.Image:
        src_w, src_h = img.size
        if src_w <= 0 or src_h <= 0:
            return Image.new("RGB", (width, height), (20, 20, 28))
        scale = max(width / src_w, height / src_h)
        nw, nh = max(1, int(src_w * scale)), max(1, int(src_h * scale))
        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = max(0, (nw - width) // 2)
        top = max(0, (nh - height) // 2)
        return resized.crop((left, top, left + width, top + height))

    @classmethod
    def _render_ai_lyric_placeholder(cls, width: int, height: int) -> Image.Image:
        """Distinct card thumbnail for the AI Lyric Scene theme before a project image exists."""
        from PIL import ImageDraw, ImageFont

        img = Image.new("RGB", (width, height), (11, 18, 32))
        draw = ImageDraw.Draw(img)
        for y in range(height):
            t = y / max(1, height - 1)
            r = int(11 + (14 - 11) * t)
            g = int(18 + (99 - 18) * t)
            b = int(32 + (233 - 32) * t)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        # Soft orbs suggesting generative atmosphere
        for cx, cy, rad, color in (
            (int(width * 0.28), int(height * 0.42), int(min(width, height) * 0.28), (99, 102, 241, 90)),
            (int(width * 0.72), int(height * 0.55), int(min(width, height) * 0.22), (14, 165, 233, 80)),
        ):
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)
            od.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=color)
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)
        label = "AI Lyric Scene"
        try:
            font = ImageFont.truetype("arial.ttf", max(18, width // 18))
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((width - tw) / 2, (height - th) / 2), label, fill=(224, 242, 254), font=font)
        return img

    @classmethod
    def _spec_photo(cls, width: int, height: int, theme: Dict[str, Any]) -> Image.Image:
        """Load a real-world / worship plate and cover-crop to the canvas."""
        asset = theme.get("asset")
        colors = theme.get("colors") or {}
        fallback = cls._hex_rgb(colors.get("base"), (16, 12, 24))
        if not asset:
            return Image.new("RGB", (width, height), fallback)
        path = cls._asset_path(asset)
        if not path.exists():
            return Image.new("RGB", (width, height), fallback)
        with Image.open(path) as raw:
            return cls._cover_crop(raw.convert("RGB"), width, height)

    @classmethod
    def _render_from_spec(cls, width: int, height: int, theme: Dict[str, Any]) -> Image.Image:
        style = (theme.get("style") or "spotlight").lower()
        colors = theme.get("colors") or {}
        extras = theme.get("extras") or {}
        rng = random.Random(sum(ord(c) for c in theme.get("id", "x")) % 9973)

        if theme.get("asset") or style == "photo":
            return cls._spec_photo(width, height, theme)
        if style == "nebula":
            return cls._spec_nebula(width, height, colors, extras, rng)
        if style == "horizon":
            return cls._spec_horizon(width, height, colors, extras)
        if style == "acoustic":
            return cls._spec_acoustic(width, height, colors)
        if style == "aurora":
            return cls._spec_aurora(width, height, colors, rng)
        if style == "minimal":
            return cls._spec_minimal(width, height, colors)
        if style == "neon":
            return cls._spec_neon(width, height, colors, extras)
        if style == "golden":
            return cls._spec_golden(width, height, colors, extras, rng)
        if style == "lounge":
            return cls._spec_lounge(width, height, colors)
        if style == "grain":
            return cls._spec_grain(width, height, colors, extras, rng)
        if style == "paper":
            return cls._spec_paper(width, height, colors)
        return cls._spec_spotlight(width, height, colors)

    @classmethod
    def _spec_spotlight(cls, width, height, colors):
        base = cls._hex_rgb(colors.get("base"), (24, 6, 14))
        spot = cls._hex_rgb(colors.get("spot"), (123, 17, 46))
        glow = cls._hex_rgb(colors.get("glow"), spot)
        img = Image.new("RGB", (width, height), color=base)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        cx, cy = width // 2, int(height * 0.45)
        draw.ellipse([cx - int(width * 0.28), cy - int(height * 0.32), cx + int(width * 0.28), cy + int(height * 0.32)], fill=(*spot, 200))
        draw.ellipse([cx - int(width * 0.14), cy - int(height * 0.18), cx + int(width * 0.14), cy + int(height * 0.18)], fill=(*glow, 130))
        layer = layer.filter(ImageFilter.GaussianBlur(85))
        img.paste(layer, (0, 0), layer)
        return img

    @classmethod
    def _spec_nebula(cls, width, height, colors, extras, rng):
        base = cls._hex_rgb(colors.get("base"), (18, 8, 28))
        mid = cls._hex_rgb(colors.get("mid"), (43, 18, 64))
        spot = cls._hex_rgb(colors.get("spot"), (74, 21, 75))
        img = Image.new("RGB", (width, height), color=base)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        for _ in range(7):
            x = rng.randint(-width // 8, width)
            y = rng.randint(-height // 8, height)
            rw = rng.randint(width // 5, width // 2)
            rh = rng.randint(height // 6, height // 2)
            col = spot if rng.random() > 0.4 else mid
            draw.ellipse([x, y, x + rw, y + rh], fill=(*col, rng.randint(60, 140)))
        layer = layer.filter(ImageFilter.GaussianBlur(70))
        img.paste(layer, (0, 0), layer)
        if extras.get("stars"):
            stars = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            sdraw = ImageDraw.Draw(stars)
            for _ in range(140):
                x, y = rng.randint(0, width - 1), rng.randint(0, height - 1)
                r = rng.randint(1, 2)
                sdraw.ellipse([x, y, x + r, y + r], fill=(255, 255, 255, rng.randint(90, 200)))
            img.paste(stars, (0, 0), stars)
        return img

    @classmethod
    def _spec_horizon(cls, width, height, colors, extras):
        top = cls._hex_rgb(colors.get("top"), (30, 27, 75))
        mid = cls._hex_rgb(colors.get("mid"), (190, 24, 93))
        bottom = cls._hex_rgb(colors.get("bottom"), (249, 115, 22))
        img = Image.new("RGB", (width, height), color=top)
        draw = ImageDraw.Draw(img)
        for y in range(height):
            t = y / max(1, height - 1)
            if t < 0.45:
                u = t / 0.45
                c = tuple(int(top[i] * (1 - u) + mid[i] * u) for i in range(3))
            else:
                u = (t - 0.45) / 0.55
                c = tuple(int(mid[i] * (1 - u) + bottom[i] * u) for i in range(3))
            draw.line([(0, y), (width, y)], fill=c)
        if extras.get("grid") or colors.get("grid"):
            grid = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            gdraw = ImageDraw.Draw(grid)
            gcol = cls._hex_rgb(colors.get("grid") or colors.get("accent"), (244, 114, 182))
            horizon = int(height * 0.58)
            for i in range(1, 14):
                y = horizon + int((height - horizon) * (i / 14) ** 1.6)
                gdraw.line([(0, y), (width, y)], fill=(*gcol, 90), width=1)
            for i in range(-8, 9):
                gdraw.line([(width // 2 + i * 90, horizon), (width // 2 + i * 220, height)], fill=(*gcol, 70), width=1)
            img.paste(grid, (0, 0), grid)
        return img

    @classmethod
    def _spec_acoustic(cls, width, height, colors):
        base = cls._hex_rgb(colors.get("base"), (15, 23, 42))
        slat = cls._hex_rgb(colors.get("slat"), (30, 41, 59))
        glow = cls._hex_rgb(colors.get("glow"), (120, 53, 15))
        img = Image.new("RGB", (width, height), color=base)
        draw = ImageDraw.Draw(img)
        gap = max(10, width // 48)
        for x in range(0, width, gap):
            draw.rectangle([x, 0, x + max(3, gap // 3), height], fill=slat)
        wash = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        wdraw = ImageDraw.Draw(wash)
        wdraw.ellipse([width * 0.2, height * 0.15, width * 0.8, height * 0.85], fill=(*glow, 90))
        wash = wash.filter(ImageFilter.GaussianBlur(90))
        img.paste(wash, (0, 0), wash)
        return img

    @classmethod
    def _spec_aurora(cls, width, height, colors, rng):
        base = cls._hex_rgb(colors.get("base"), (2, 44, 34))
        w1 = cls._hex_rgb(colors.get("wave1"), (5, 150, 105))
        w2 = cls._hex_rgb(colors.get("wave2"), (52, 211, 153))
        img = Image.new("RGB", (width, height), color=base)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        for i in range(6):
            y = int(height * (0.15 + i * 0.12))
            amp = height // 10
            points = []
            for x in range(0, width + 1, 24):
                yy = y + int(math.sin((x / width) * math.pi * 2 + i) * amp)
                points.append((x, yy))
            for x, yy in points:
                col = w1 if i % 2 == 0 else w2
                draw.ellipse([x - 40, yy - 28, x + 40, yy + 28], fill=(*col, 55))
        layer = layer.filter(ImageFilter.GaussianBlur(40))
        img.paste(layer, (0, 0), layer)
        return img

    @classmethod
    def _spec_minimal(cls, width, height, colors):
        base = cls._hex_rgb(colors.get("base"), (11, 18, 32))
        frame = cls._hex_rgb(colors.get("frame"), (51, 65, 85))
        img = Image.new("RGB", (width, height), color=base)
        draw = ImageDraw.Draw(img)
        m = min(width, height) // 18
        draw.rectangle([m, m, width - m, height - m], outline=frame, width=2)
        draw.line([(m, height // 2), (m + 28, height // 2)], fill=frame, width=2)
        draw.line([(width - m - 28, height // 2), (width - m, height // 2)], fill=frame, width=2)
        vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        vdraw = ImageDraw.Draw(vignette)
        vdraw.rectangle([0, 0, width, height], fill=(0, 0, 0, 90))
        vdraw.ellipse([width * 0.1, height * 0.08, width * 0.9, height * 0.92], fill=(0, 0, 0, 0))
        vignette = vignette.filter(ImageFilter.GaussianBlur(40))
        # rebuild clean vignette differently
        img = Image.composite(Image.new("RGB", (width, height), (0, 0, 0)), img, Image.new("L", (width, height), 40))
        # simpler approach: redraw base with center lift
        img = Image.new("RGB", (width, height), color=base)
        draw = ImageDraw.Draw(img)
        draw.rectangle([m, m, width - m, height - m], outline=frame, width=2)
        lift = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(lift).ellipse([width * 0.2, height * 0.15, width * 0.8, height * 0.85], fill=(255, 255, 255, 18))
        lift = lift.filter(ImageFilter.GaussianBlur(60))
        img.paste(lift, (0, 0), lift)
        draw = ImageDraw.Draw(img)
        draw.rectangle([m, m, width - m, height - m], outline=frame, width=2)
        return img

    @classmethod
    def _spec_neon(cls, width, height, colors, extras):
        base = cls._hex_rgb(colors.get("base"), (2, 6, 23))
        cyan = cls._hex_rgb(colors.get("cyan"), (6, 182, 212))
        magenta = cls._hex_rgb(colors.get("magenta"), (225, 29, 72))
        img = Image.new("RGB", (width, height), color=base)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        draw.line([(int(width * 0.15), int(height * 0.2)), (int(width * 0.85), int(height * 0.35))], fill=(*cyan, 200), width=6)
        draw.line([(int(width * 0.2), int(height * 0.75)), (int(width * 0.9), int(height * 0.55))], fill=(*magenta, 200), width=6)
        draw.ellipse([width * 0.55, height * 0.15, width * 0.95, height * 0.55], outline=(*cyan, 160), width=4)
        draw.ellipse([width * 0.05, height * 0.45, width * 0.45, height * 0.9], outline=(*magenta, 140), width=4)
        layer = layer.filter(ImageFilter.GaussianBlur(8))
        img.paste(layer, (0, 0), layer)
        glow = layer.filter(ImageFilter.GaussianBlur(28))
        img.paste(glow, (0, 0), glow)
        return img

    @classmethod
    def _spec_golden(cls, width, height, colors, extras, rng):
        base = cls._hex_rgb(colors.get("base"), (28, 16, 6))
        sun = cls._hex_rgb(colors.get("sun"), (245, 158, 11))
        glow = cls._hex_rgb(colors.get("glow"), (253, 186, 116))
        img = Image.new("RGB", (width, height), color=base)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        cx, cy = int(width * 0.7), int(height * 0.35)
        draw.ellipse([cx - 180, cy - 180, cx + 180, cy + 180], fill=(*sun, 180))
        draw.ellipse([cx - 320, cy - 260, cx + 320, cy + 260], fill=(*glow, 70))
        layer = layer.filter(ImageFilter.GaussianBlur(50))
        img.paste(layer, (0, 0), layer)
        if extras.get("bokeh"):
            bokeh = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            bdraw = ImageDraw.Draw(bokeh)
            for _ in range(35):
                x, y = rng.randint(0, width), rng.randint(0, height)
                r = rng.randint(8, 28)
                bdraw.ellipse([x, y, x + r, y + r], fill=(*glow, rng.randint(25, 70)))
            bokeh = bokeh.filter(ImageFilter.GaussianBlur(2))
            img.paste(bokeh, (0, 0), bokeh)
        return img

    @classmethod
    def _spec_lounge(cls, width, height, colors):
        base = cls._hex_rgb(colors.get("base"), (2, 6, 23))
        spot = cls._hex_rgb(colors.get("spot"), (29, 78, 216))
        glow = cls._hex_rgb(colors.get("glow"), (96, 165, 250))
        img = Image.new("RGB", (width, height), color=base)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        cx, cy = width // 2, int(height * 0.4)
        draw.ellipse([cx - int(width * 0.22), cy - int(height * 0.2), cx + int(width * 0.22), cy + int(height * 0.35)], fill=(*spot, 170))
        draw.ellipse([cx - 90, cy - 70, cx + 90, cy + 90], fill=(*glow, 110))
        layer = layer.filter(ImageFilter.GaussianBlur(70))
        img.paste(layer, (0, 0), layer)
        return img

    @classmethod
    def _spec_grain(cls, width, height, colors, extras, rng):
        base = cls._hex_rgb(colors.get("base"), (30, 16, 48))
        wash = cls._hex_rgb(colors.get("wash"), (168, 85, 247))
        soft = cls._hex_rgb(colors.get("soft"), (240, 171, 252))
        img = Image.new("RGB", (width, height), color=base)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        draw.ellipse([-width * 0.1, -height * 0.1, width * 0.8, height * 0.7], fill=(*wash, 110))
        draw.ellipse([width * 0.3, height * 0.35, width * 1.1, height * 1.1], fill=(*soft, 70))
        layer = layer.filter(ImageFilter.GaussianBlur(80))
        img.paste(layer, (0, 0), layer)
        if extras.get("grain", True):
            grain = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            gdraw = ImageDraw.Draw(grain)
            for _ in range(5000):
                x, y = rng.randint(0, width - 1), rng.randint(0, height - 1)
                gdraw.point((x, y), fill=(255, 255, 255, rng.randint(10, 40)))
            img.paste(grain, (0, 0), grain)
        return img

    @classmethod
    def _spec_paper(cls, width, height, colors):
        base = cls._hex_rgb(colors.get("base"), (28, 20, 8))
        wash = cls._hex_rgb(colors.get("wash"), (113, 63, 18))
        line = cls._hex_rgb(colors.get("line"), (161, 98, 7))
        img = Image.new("RGB", (width, height), color=base)
        layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rectangle([0, 0, width, height], fill=(*wash, 70))
        layer = layer.filter(ImageFilter.GaussianBlur(40))
        img.paste(layer, (0, 0), layer)
        draw = ImageDraw.Draw(img)
        for y in range(int(height * 0.2), int(height * 0.85), max(28, height // 28)):
            draw.line([(int(width * 0.12), y), (int(width * 0.88), y)], fill=line, width=1)
        return img

    @classmethod
    def generate_template_asset(
        cls,
        pattern_type: str = "burgundy_studio",
        output_path: Optional[Path] = None,
        width: int = 1920,
        height: int = 1080,
        fmt: str = "WEBP"
    ) -> Path:
        """
        Generates and saves a lightweight template image (WebP or PNG).
        """
        img = cls.generate_pattern_image(pattern_type, width=width, height=height)
        if output_path is None:
            output_path = Path(f"template_{pattern_type}.webp" if fmt.upper() == "WEBP" else f"template_{pattern_type}.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if fmt.upper() == "WEBP":
                img.save(output_path, "WEBP", quality=82, method=6)
            else:
                img.save(output_path, "PNG", optimize=True)
        except Exception:
            img.save(output_path, "PNG")
        return output_path

    @classmethod
    def _draw_visualizer_bars(
        cls,
        img: Image.Image,
        frame_i: int,
        fps: int,
        bar_count: int,
        color: Tuple[int, int, int],
    ) -> None:
        """Paint bold bouncing spectrum bars (clearly readable as motion video)."""
        w, h = img.size
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        margin_x = int(w * 0.04)
        usable = max(1, w - 2 * margin_x)
        gap = max(2, usable // (bar_count * 4))
        bar_w = max(3, (usable - gap * (bar_count - 1)) // bar_count)
        baseline = int(h * 0.92)
        max_h = int(h * 0.38)
        t = frame_i / float(fps)
        center = max(1.0, (bar_count - 1) / 2.0)
        for b in range(bar_count):
            phase = b * 0.42
            amp = (
                0.35
                + 0.42 * math.sin(t * 8.4 + phase)
                + 0.28 * math.sin(t * 14.2 + phase * 1.7)
                + 0.18 * math.sin(t * 4.1 + b * 0.11)
                + 0.10 * math.sin(t * 21.0 + phase * 0.5)
            )
            envelope = 1.0 - 0.28 * abs(b - center) / center
            bh = int(max_h * max(0.12, min(1.0, amp)) * envelope)
            x0 = margin_x + b * (bar_w + gap)
            y0 = baseline - bh
            # Soft glow behind each bar
            glow = max(4, bar_w)
            draw.rectangle(
                [x0 - 1, y0 - 2, x0 + bar_w + 1, baseline],
                fill=(*color, 55),
            )
            draw.rectangle([x0, y0, x0 + bar_w - 1, baseline], fill=(*color, 245))
            tip = max(2, bar_w // 2)
            draw.rectangle([x0, y0, x0 + bar_w - 1, min(baseline, y0 + tip)], fill=(255, 255, 255, 180))
            draw.rectangle(
                [x0, baseline + 2, x0 + bar_w - 1, baseline + 2 + max(3, bh // 2)],
                fill=(*color, 70),
            )
        img.paste(layer, (0, 0), layer)

    @classmethod
    def _draw_motion_overlay(
        cls,
        img: Image.Image,
        frame_i: int,
        fps: int,
        motion: str,
        theme: Dict[str, Any],
        rng: random.Random,
    ) -> None:
        """Animate pulse / starfield / waves / grid overlays onto a still plate."""
        w, h = img.size
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        colors = theme.get("colors") or {}
        t = frame_i / float(fps)
        accent = cls._hex_rgb(colors.get("accent") or colors.get("glow") or "#FFFFFF", (255, 255, 255))
        glow = cls._hex_rgb(colors.get("glow") or colors.get("spot") or colors.get("wave1") or "#94A3B8", accent)
        grid_c = cls._hex_rgb(colors.get("grid") or colors.get("accent") or "#22D3EE", (34, 211, 238))

        if motion == "pulse":
            breath = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * 2.6))
            cx, cy = w // 2, int(h * 0.42)
            rx = int(w * (0.18 + 0.22 * breath))
            ry = int(h * (0.16 + 0.20 * breath))
            alpha = int(50 + 110 * breath)
            draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(*glow, alpha))
            draw.ellipse(
                [cx - rx // 2, cy - ry // 2, cx + rx // 2, cy + ry // 2],
                fill=(*accent, int(alpha * 0.55)),
            )
            layer = layer.filter(ImageFilter.GaussianBlur(28))
        elif motion == "starfield":
            count = 90
            band = max(1, int(h * 0.78))
            for i in range(count):
                # Stable star layout; only drift/twinkle over time.
                x0 = (i * 97 + 13) % w
                y0 = (i * 53 + 29) % band
                x = int((x0 + t * (6 + (i % 5) * 2)) % w)
                y = int((y0 + math.sin(t * 1.2 + i * 0.35) * 3) % band)
                twinkle = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 5.5 + i * 0.7))
                r = 1 if (i % 5) else 2
                a = int(90 + 150 * twinkle)
                draw.ellipse([x - r, y - r, x + r, y + r], fill=(*accent, a))
        elif motion == "waves":
            c1 = cls._hex_rgb(colors.get("wave1") or "#059669", (5, 150, 105))
            c2 = cls._hex_rgb(colors.get("wave2") or "#34D399", (52, 211, 153))
            for band, col in ((0, c1), (1, c2)):
                pts = []
                y_base = int(h * (0.38 + band * 0.14))
                amp = int(h * (0.05 + band * 0.02))
                for x in range(0, w + 8, 8):
                    y = y_base + int(amp * math.sin(t * 2.2 + x * 0.012 + band))
                    pts.append((x, y))
                for i in range(len(pts) - 1):
                    draw.line([pts[i], pts[i + 1]], fill=(*col, 140 - band * 30), width=6 - band)
            layer = layer.filter(ImageFilter.GaussianBlur(3))
        elif motion == "grid":
            # Perspective-ish scrolling neon floor grid.
            horizon = int(h * 0.48)
            scroll = (t * 42) % 36
            for i in range(18):
                y = horizon + int((i * 18 + scroll) * (1 + i * 0.08))
                if y >= h:
                    break
                alpha = max(40, 180 - i * 8)
                draw.line([(0, y), (w, y)], fill=(*grid_c, alpha), width=1)
            vanishing_x = w // 2
            for k in range(-10, 11):
                x_bottom = vanishing_x + int(k * w * 0.08)
                draw.line([(vanishing_x, horizon), (x_bottom, h)], fill=(*grid_c, 120), width=1)
            sun_y = horizon - int(h * 0.08)
            sun_r = int(min(w, h) * 0.08)
            draw.ellipse(
                [vanishing_x - sun_r, sun_y - sun_r, vanishing_x + sun_r, sun_y + sun_r],
                fill=(*accent, 90),
            )

        img.paste(layer, (0, 0), layer)

    @classmethod
    def _prepare_visualizer_base(
        cls,
        pattern_type: str,
        width: int,
        height: int,
        theme: Dict[str, Any],
    ) -> Image.Image:
        base = cls.generate_pattern_image(pattern_type, width, height).convert("RGB")
        extras = theme.get("extras") or {}
        if not extras.get("clear_lower", True):
            return base
        colors = theme.get("colors") or {}
        fill = cls._hex_rgb(
            colors.get("bottom") or colors.get("base") or colors.get("mid"),
            (20, 10, 40),
        )
        band_top = int(height * 0.78)
        # Soft blend into the bar band so procedural gradients keep atmosphere.
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        for y in range(band_top, height):
            t = (y - band_top) / max(1, height - band_top)
            alpha = int(40 + 215 * t)
            odraw.line([(0, y), (width, y)], fill=(*fill, alpha))
        base = base.convert("RGBA")
        base = Image.alpha_composite(base, overlay).convert("RGB")
        return base

    @classmethod
    def _encode_frame_dir(cls, tmp: Path, output_path: Path, fps: int) -> None:
        ffmpeg = get_ffmpeg_binary()
        cmd = [
            ffmpeg, "-y",
            "-framerate", str(fps),
            "-i", str(tmp / "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "veryfast",
            "-crf", "23",
            "-an",
            "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0 or not output_path.exists():
            detail = (result.stderr or "")[-800:]
            raise RuntimeError(f"Could not build theme video loop: {detail}")

    @classmethod
    def _generate_visualizer_loop(
        cls,
        pattern_type: str,
        output_path: Path,
        width: int,
        height: int,
        seconds: float,
        theme: Dict[str, Any],
    ) -> Path:
        """Frame-sequence video with bouncing audio-visualizer bars."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fps = 24
        n_frames = int(max(4.0, float(seconds)) * fps)
        extras = theme.get("extras") or {}
        bar_count = max(24, min(128, int(extras.get("bars") or 64)))
        bar_color = cls._hex_rgb(
            extras.get("bar_color") or (theme.get("colors") or {}).get("accent") or "#FFFFFF",
            (255, 255, 255),
        )
        base = cls._prepare_visualizer_base(pattern_type, width, height, theme)
        tmp = Path(tempfile.mkdtemp(prefix="lyric_viz_"))
        try:
            for i in range(n_frames):
                frame = base.copy()
                cls._draw_visualizer_bars(frame, i, fps, bar_count, bar_color)
                frame.save(tmp / f"frame_{i:04d}.png", "PNG")
            cls._encode_frame_dir(tmp, output_path, fps)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return output_path

    @classmethod
    def _generate_animated_loop(
        cls,
        pattern_type: str,
        output_path: Path,
        width: int,
        height: int,
        seconds: float,
        theme: Dict[str, Any],
        motion: str,
    ) -> Path:
        """Frame-sequence video for pulse / starfield / waves / grid motion beds."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fps = 24
        n_frames = int(max(4.0, float(seconds)) * fps)
        base = cls.generate_pattern_image(pattern_type, width, height).convert("RGB")
        rng = random.Random(sum(ord(c) for c in pattern_type) % 9973)
        tmp = Path(tempfile.mkdtemp(prefix="lyric_motion_"))
        try:
            for i in range(n_frames):
                frame = base.copy()
                cls._draw_motion_overlay(frame, i, fps, motion, theme, rng)
                frame.save(tmp / f"frame_{i:04d}.png", "PNG")
            cls._encode_frame_dir(tmp, output_path, fps)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return output_path

    @classmethod
    def generate_theme_video_loop(
        cls,
        pattern_type: str,
        output_path: Path,
        width: int = 1920,
        height: int = 1080,
        seconds: float = 8.0,
    ) -> Path:
        """Create a short silent looping motion bed with real animated frames."""
        theme = get_theme(pattern_type) or {}
        motion = (theme.get("motion") or "visualizer").lower()
        if motion == "visualizer":
            return cls._generate_visualizer_loop(
                pattern_type, output_path, width, height, seconds, theme
            )
        if motion in ("pulse", "starfield", "waves", "grid"):
            return cls._generate_animated_loop(
                pattern_type, output_path, width, height, seconds, theme, motion
            )
        # Fallback for any unexpected video theme: bold visualizer bars.
        return cls._generate_visualizer_loop(
            pattern_type, output_path, width, height, seconds, theme
        )

    @staticmethod
    def _render_burgundy_studio(width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color=(24, 6, 14))
        spot = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(spot)
        cx, cy = width // 2, int(height * 0.45)
        sdraw.ellipse([cx - int(width*0.25), cy - int(height*0.3), cx + int(width*0.25), cy + int(height*0.3)], fill=(123, 17, 46, 210))
        sdraw.ellipse([cx - int(width*0.14), cy - int(height*0.18), cx + int(width*0.14), cy + int(height*0.18)], fill=(168, 28, 65, 140))
        sdraw.polygon([(cx - 80, 0), (cx + 80, 0), (cx + int(width*0.35), height), (cx - int(width*0.35), height)], fill=(130, 20, 50, 70))
        spot = spot.filter(ImageFilter.GaussianBlur(80))
        img.paste(spot, (0, 0), spot)

        slat_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        slat_draw = ImageDraw.Draw(slat_layer)
        slat_width = max(24, int(width * 0.02))
        slat_gap = max(10, int(width * 0.008))
        for x in range(30, width - 30, slat_width + slat_gap):
            slat_draw.rectangle([x, 30, x + slat_width, height - 30], outline=(38, 12, 22, 120), width=1)
            slat_draw.line([(x + 2, 30), (x + 2, height - 30)], fill=(65, 20, 36, 90), width=1)
        img.paste(slat_layer, (0, 0), slat_layer)

        vig = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        vdraw = ImageDraw.Draw(vig)
        vdraw.rectangle([0, 0, width, height], fill=(10, 2, 6, 90))
        vdraw.ellipse([width * 0.12, height * 0.08, width * 0.88, height * 0.92], fill=(0, 0, 0, 0))
        vig = vig.filter(ImageFilter.GaussianBlur(90))
        img.paste(vig, (0, 0), vig)
        return img

    @staticmethod
    def _render_deep_nebula(width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color=(8, 8, 20))
        cx, cy = width // 2, height // 2
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.ellipse([cx - int(width*0.22), cy - int(height*0.25), cx + int(width*0.2), cy + int(height*0.24)], fill=(65, 22, 110, 180))
        draw.ellipse([cx - int(width*0.12), cy - int(height*0.14), cx + int(width*0.11), cy + int(height*0.13)], fill=(105, 40, 160, 150))
        draw.ellipse([int(width * 0.2) - 180, int(height * 0.35) - 150, int(width * 0.2) + 180, int(height * 0.35) + 150], fill=(22, 60, 125, 160))
        draw.ellipse([int(width * 0.82) - 200, int(height * 0.68) - 180, int(width * 0.82) + 200, int(height * 0.68) + 180], fill=(120, 30, 95, 150))
        overlay = overlay.filter(ImageFilter.GaussianBlur(85))
        img.paste(overlay, (0, 0), overlay)

        rnd = random.Random(42)
        star_draw = ImageDraw.Draw(img)
        for _ in range(320):
            sx = rnd.randint(15, width - 15)
            sy = rnd.randint(15, height - 15)
            brightness = rnd.randint(150, 255)
            size = rnd.choice([1, 1, 1, 2, 2, 3])
            tint = rnd.choice([(brightness, brightness, brightness), (brightness - 30, brightness - 10, brightness), (brightness, brightness - 30, brightness - 10)])
            star_draw.ellipse([sx, sy, sx + size, sy + size], fill=tint)
        return img

    @staticmethod
    def _render_retrowave_sunset(width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color=(15, 8, 30))
        draw = ImageDraw.Draw(img)
        horizon_y = int(height * 0.62)
        for y in range(horizon_y):
            prog = y / horizon_y
            r = int(20 + 175 * (prog ** 1.4))
            g = int(10 + 40 * (prog ** 1.8))
            b = int(35 + 85 * (1.0 - prog))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        cx = width // 2
        sun_r = int(min(width, height) * 0.18)
        sun_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(sun_overlay)
        sdraw.ellipse([cx - sun_r, horizon_y - sun_r, cx + sun_r, horizon_y + sun_r], fill=(255, 140, 50, 230))
        for slice_y in range(horizon_y - sun_r + int(sun_r * 0.3), horizon_y, 14):
            sdraw.rectangle([cx - sun_r - 10, slice_y, cx + sun_r + 10, slice_y + 4], fill=(15, 8, 30, 255))
        img.paste(sun_overlay, (0, 0), sun_overlay)

        draw.rectangle([0, horizon_y, width, height], fill=(12, 5, 20))
        draw.line([(0, horizon_y), (width, horizon_y)], fill=(245, 60, 140), width=3)
        num_lines = 24
        for i in range(-num_lines, num_lines + 1):
            target_x = cx + i * int(width * 0.045)
            draw.line([(cx, horizon_y), (target_x, height)], fill=(180, 30, 110), width=2)

        y = horizon_y + 12
        step = 8
        while y < height:
            draw.line([(0, int(y)), (width, int(y))], fill=(160, 25, 95), width=1)
            step = int(step * 1.32)
            y += step
        return img

    @staticmethod
    def _render_midnight_acoustic(width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color=(20, 22, 26))
        draw = ImageDraw.Draw(img)
        panel_w = max(24, int(width * 0.026))
        gap = max(8, int(width * 0.007))
        for x in range(30, width - 30, panel_w + gap):
            draw.rectangle([x, 50, x + panel_w, height - 50], fill=(28, 26, 25), outline=(42, 38, 36), width=1)
            draw.line([(x + 1, 50), (x + 1, height - 50)], fill=(52, 46, 42), width=1)

        cx = width // 2
        light_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ldraw = ImageDraw.Draw(light_overlay)
        max_r = int(min(width, height) * 0.6)
        for r in range(max_r, 0, -25):
            alpha = int((1.0 - (r / float(max_r))) ** 1.8 * 65)
            ldraw.ellipse([cx - r, -100, cx + r, int(r * 1.1)], fill=(220, 180, 130, alpha))
        img.paste(light_overlay, (0, 0), light_overlay)

        vr_x, vr_y = int(width * 0.85), int(height * 0.2)
        vinyl_draw = ImageDraw.Draw(img)
        for gr in range(40, 340, 20):
            vinyl_draw.ellipse([vr_x - gr, vr_y - gr, vr_x + gr, vr_y + gr], outline=(38, 40, 46), width=1)
        return img

    @staticmethod
    def _render_abstract_aurora(width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color=(8, 22, 24))
        curves = [
            {"color": (5, 150, 105, 55), "freq": 0.003, "phase": 0.0, "amp": 90, "base_y": height * 0.48, "width": 80},
            {"color": (16, 185, 129, 65), "freq": 0.004, "phase": 1.5, "amp": 120, "base_y": height * 0.52, "width": 60},
            {"color": (6, 95, 70, 70), "freq": 0.0025, "phase": 3.0, "amp": 100, "base_y": height * 0.56, "width": 90},
            {"color": (20, 184, 166, 50), "freq": 0.005, "phase": 4.5, "amp": 70, "base_y": height * 0.44, "width": 50},
        ]
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        for c in curves:
            pts = []
            for x in range(0, width + 10, 8):
                y = c["base_y"] + math.sin(x * c["freq"] + c["phase"]) * c["amp"] + math.cos(x * 0.002) * (c["amp"] * 0.5)
                pts.append((x, int(y)))
            for w in range(-c["width"] // 2, c["width"] // 2, 4):
                shifted = [(px, py + w) for px, py in pts]
                alpha = int(c["color"][3] * (1.0 - abs(w) / (c["width"] / 2)))
                odraw.line(shifted, fill=(c["color"][0], c["color"][1], c["color"][2], alpha), width=4)
        img.paste(overlay, (0, 0), overlay)
        return img

    @staticmethod
    def _render_minimal_dark(width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color=(18, 20, 24))
        cx, cy = width // 2, height // 2
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        max_r = int(math.hypot(cx, cy))
        for r in range(max_r, 0, -30):
            factor = 1.0 - (r / max_r)
            shade = int(18 + 22 * (factor ** 2.0))
            odraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(shade, shade + 3, shade + 8, int(255 * (1.0 - factor * 0.5))))
        img.paste(overlay, (0, 0), overlay)

        fdraw = ImageDraw.Draw(img)
        frame_pad = int(min(width, height) * 0.05)
        color = (60, 68, 80)
        mark_len = 28
        fdraw.line([(frame_pad, frame_pad), (frame_pad + mark_len, frame_pad)], fill=color, width=2)
        fdraw.line([(frame_pad, frame_pad), (frame_pad, frame_pad + mark_len)], fill=color, width=2)
        fdraw.line([(width - frame_pad, frame_pad), (width - frame_pad - mark_len, frame_pad)], fill=color, width=2)
        fdraw.line([(width - frame_pad, frame_pad), (width - frame_pad, frame_pad + mark_len)], fill=color, width=2)
        fdraw.line([(frame_pad, height - frame_pad), (frame_pad + mark_len, height - frame_pad)], fill=color, width=2)
        fdraw.line([(frame_pad, height - frame_pad), (frame_pad + mark_len, height - frame_pad - mark_len)], fill=color, width=2)
        fdraw.line([(width - frame_pad, height - frame_pad), (width - frame_pad - mark_len, height - frame_pad)], fill=color, width=2)
        fdraw.line([(width - frame_pad, height - frame_pad), (width - frame_pad, height - frame_pad - mark_len)], fill=color, width=2)

        fdraw.line([(cx - 15, cy), (cx + 15, cy)], fill=(45, 52, 64), width=1)
        fdraw.line([(cx, cy - 15), (cx, cy + 15)], fill=(45, 52, 64), width=1)
        return img

    @staticmethod
    def _render_cyberpunk_neon(width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color=(10, 8, 22))
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        cx, cy = width // 2, height // 2

        # Glowing cyan and magenta neon beams
        odraw.line([(0, int(height * 0.32)), (width, int(height * 0.22))], fill=(6, 182, 212, 220), width=24)
        odraw.line([(0, int(height * 0.78)), (width, int(height * 0.68))], fill=(236, 72, 153, 220), width=24)
        odraw.ellipse([cx - int(width*0.22), cy - int(height*0.22), cx + int(width*0.22), cy + int(height*0.22)], fill=(139, 92, 246, 120))
        overlay = overlay.filter(ImageFilter.GaussianBlur(50))
        img.paste(overlay, (0, 0), overlay)

        # Crisp laser neon cores
        laser = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ldraw = ImageDraw.Draw(laser)
        ldraw.line([(0, int(height * 0.32)), (width, int(height * 0.22))], fill=(200, 250, 255, 230), width=3)
        ldraw.line([(0, int(height * 0.78)), (width, int(height * 0.68))], fill=(255, 210, 240, 230), width=3)
        img.paste(laser, (0, 0), laser)

        draw = ImageDraw.Draw(img)
        for x in range(0, width, 120):
            draw.line([(x, 0), (x, height)], fill=(28, 25, 48), width=1)
        for y in range(0, height, 120):
            draw.line([(0, y), (width, y)], fill=(28, 25, 48), width=1)
        return img

    @staticmethod
    def _render_golden_hour(width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color=(26, 16, 10))
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        cx, cy = width // 2, int(height * 0.4)
        odraw.ellipse([cx - int(width*0.3), cy - int(height*0.3), cx + int(width*0.3), cy + int(height*0.3)], fill=(245, 158, 11, 200))
        odraw.ellipse([cx - int(width*0.16), cy - int(height*0.16), cx + int(width*0.16), cy + int(height*0.16)], fill=(251, 191, 36, 170))
        overlay = overlay.filter(ImageFilter.GaussianBlur(85))
        img.paste(overlay, (0, 0), overlay)

        rnd = random.Random(101)
        b_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        bdraw = ImageDraw.Draw(b_layer)
        for _ in range(45):
            bx = rnd.randint(50, width - 50)
            by = rnd.randint(50, height - 50)
            br = rnd.randint(8, 32)
            bdraw.ellipse([bx - br, by - br, bx + br, by + br], fill=(253, 230, 138, rnd.randint(25, 65)))
        b_layer = b_layer.filter(ImageFilter.GaussianBlur(8))
        img.paste(b_layer, (0, 0), b_layer)
        return img

    @staticmethod
    def _render_velvet_lounge(width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color=(10, 14, 28))
        cx, cy = width // 2, int(height * 0.45)
        spot = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        sdraw = ImageDraw.Draw(spot)
        sdraw.ellipse([cx - int(width*0.28), cy - int(height*0.3), cx + int(width*0.28), cy + int(height*0.3)], fill=(30, 58, 138, 220))
        sdraw.ellipse([cx - int(width*0.14), cy - int(height*0.16), cx + int(width*0.14), cy + int(height*0.16)], fill=(59, 130, 246, 140))
        sdraw.polygon([(cx - 70, 0), (cx + 70, 0), (cx + int(width*0.3), height), (cx - int(width*0.3), height)], fill=(37, 99, 235, 60))
        spot = spot.filter(ImageFilter.GaussianBlur(80))
        img.paste(spot, (0, 0), spot)

        c_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cdraw = ImageDraw.Draw(c_layer)
        for x in range(0, width, 55):
            alpha = int(40 + math.sin(x * 0.1) * 25)
            cdraw.rectangle([x, 0, x + 28, height], fill=(15, 23, 42, alpha))
        c_layer = c_layer.filter(ImageFilter.GaussianBlur(12))
        img.paste(c_layer, (0, 0), c_layer)
        return img

    @staticmethod
    def _render_lofi_chill(width: int, height: int) -> Image.Image:
        img = Image.new("RGB", (width, height), color=(22, 16, 26))
        cx, cy = width // 2, height // 2
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.ellipse([cx - int(width*0.28), cy - int(height*0.28), cx + int(width*0.28), cy + int(height*0.28)], fill=(168, 85, 247, 120))
        odraw.ellipse([cx - int(width*0.16), cy - int(height*0.16), cx + int(width*0.16), cy + int(height*0.16)], fill=(244, 114, 182, 110))
        overlay = overlay.filter(ImageFilter.GaussianBlur(90))
        img.paste(overlay, (0, 0), overlay)

        t_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        tdraw = ImageDraw.Draw(t_layer)
        for y in range(0, height, 8):
            tdraw.line([(0, y), (width, y)], fill=(10, 8, 14, 45), width=1)
        img.paste(t_layer, (0, 0), t_layer)
        return img

    @classmethod
    def generate_background_video(
        cls,
        audio_path: Path,
        output_video_path: Path,
        duration: float,
        pattern_type: str = "burgundy_studio",
        aspect_ratio: str = "16:9"
    ) -> Path:
        """
        Creates a video from the selected template and aspect ratio, muxing the audio track.
        Uses a low-frame-rate still-image video so shared-hosting requests finish quickly.
        """
        ffmpeg = get_ffmpeg_binary()
        output_video_path.parent.mkdir(parents=True, exist_ok=True)

        width, height = cls.get_dimensions(aspect_ratio)

        temp_img_path = output_video_path.parent / f"temp_pattern_bg_{output_video_path.stem}.png"
        img = cls.generate_pattern_image(pattern_type, width=width, height=height)
        img.save(temp_img_path)

        dur_str = str(max(1.0, float(duration)))

        cmd = [
            ffmpeg, "-y",
            "-loop", "1",
            "-framerate", "1",
            "-i", str(temp_img_path),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-preset", "ultrafast",
            "-r", "25",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", dur_str,
            "-shortest",
            "-movflags", "+faststart",
            "-threads", "0",
            str(output_video_path)
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if result.returncode != 0:
            detail = (result.stderr or "FFmpeg exited without diagnostic output").strip()
            raise RuntimeError(f"FFmpeg exited with code {result.returncode}: {detail[-1200:]}")

        try:
            if temp_img_path.exists():
                temp_img_path.unlink()
        except Exception:
            pass

        return output_video_path

import math
import random
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from app.services.media_probe import get_ffmpeg_binary

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

    TEMPLATES = [
        {
            "id": "burgundy_studio",
            "name": "Burgundy Studio",
            "tagline": "Luxury acoustic spotlight vignette",
            "preview_color": "#7B112E",
            "thumbnail": "/static/img/templates/burgundy_studio.png"
        },
        {
            "id": "deep_nebula",
            "name": "Deep Nebula",
            "tagline": "Cosmic indigo & violet celestial starfield",
            "preview_color": "#4A154B",
            "thumbnail": "/static/img/templates/deep_nebula.png"
        },
        {
            "id": "retrowave_sunset",
            "name": "Retrowave Dusk",
            "tagline": "80s synth horizon & neon perspective grid",
            "preview_color": "#BE185D",
            "thumbnail": "/static/img/templates/retrowave_sunset.png"
        },
        {
            "id": "midnight_acoustic",
            "name": "Midnight Acoustic",
            "tagline": "Charcoal studio wood slats & warm vinyl",
            "preview_color": "#334155",
            "thumbnail": "/static/img/templates/midnight_acoustic.png"
        },
        {
            "id": "abstract_aurora",
            "name": "Abstract Aurora",
            "tagline": "Emerald & teal ambient harmonic waves",
            "preview_color": "#059669",
            "thumbnail": "/static/img/templates/abstract_aurora.png"
        },
        {
            "id": "minimal_dark",
            "name": "Minimal Graphite",
            "tagline": "Dark carbon vignette with framing marks",
            "preview_color": "#1E293B",
            "thumbnail": "/static/img/templates/minimal_dark.png"
        },
        {
            "id": "cyberpunk_neon",
            "name": "Cyberpunk Neon",
            "tagline": "Electric cyan & magenta laser lights",
            "preview_color": "#06B6D4",
            "thumbnail": "/static/img/templates/cyberpunk_neon.png"
        },
        {
            "id": "golden_hour",
            "name": "Golden Hour",
            "tagline": "Amber sunset warmth & soft dust bokeh",
            "preview_color": "#F59E0B",
            "thumbnail": "/static/img/templates/golden_hour.png"
        },
        {
            "id": "velvet_lounge",
            "name": "Velvet Lounge",
            "tagline": "Royal sapphire & indigo stage spotlight",
            "preview_color": "#1D4ED8",
            "thumbnail": "/static/img/templates/velvet_lounge.png"
        },
        {
            "id": "lofi_chill",
            "name": "Lo-Fi Chill",
            "tagline": "Lavender pastel warmth with tape grain",
            "preview_color": "#A855F7",
            "thumbnail": "/static/img/templates/lofi_chill.png"
        },
        {
            "id": "emerald_stage",
            "name": "Emerald Stage",
            "tagline": "Deep green concert wash",
            "preview_color": "#166534",
            "thumbnail": "/static/img/templates/abstract_aurora.png"
        },
        {
            "id": "rose_film",
            "name": "Rose Film",
            "tagline": "Cinematic rose and shadow",
            "preview_color": "#9F1239",
            "thumbnail": "/static/img/templates/retrowave_sunset.png"
        },
        {
            "id": "ocean_pulse",
            "name": "Ocean Pulse",
            "tagline": "Blue motion with cool highlights",
            "preview_color": "#0369A1",
            "thumbnail": "/static/img/templates/cyberpunk_neon.png"
        },
        {
            "id": "paper_moon",
            "name": "Paper Moon",
            "tagline": "Warm editorial midnight texture",
            "preview_color": "#713F12",
            "thumbnail": "/static/img/templates/golden_hour.png"
        }
    ]

    @classmethod
    def get_templates(cls):
        return cls.TEMPLATES

    @classmethod
    def get_dimensions(cls, aspect_ratio: str = "16:9") -> tuple[int, int]:
        return cls.ASPECT_RATIOS.get(aspect_ratio, (1920, 1080))

    @classmethod
    def generate_pattern_image(cls, pattern_type: str = "burgundy_studio", width: int = 1920, height: int = 1080) -> Image.Image:
        """
        Generates a canvas pattern image based on the selected template and dimensions.
        Default: Burgundy Studio.
        """
        pattern_type = pattern_type.lower().strip() if pattern_type else "burgundy_studio"

        generators = {
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
            "emerald_stage": cls._render_abstract_aurora,
            "rose_film": cls._render_retrowave_sunset,
            "ocean_pulse": cls._render_cyberpunk_neon,
            "paper_moon": cls._render_golden_hour,
        }

        gen_func = generators.get(pattern_type, cls._render_burgundy_studio)
        return gen_func(width, height)

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
        Uses ultrafast 1fps keyframe encoding for instant 1-2 second generation.
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
            "-framerate", "30",
            "-i", str(temp_img_path),
            "-i", str(audio_path),
            "-c:v", "libx264",
            "-r", "30",
            "-preset", "ultrafast",
            "-tune", "stillimage",
            "-crf", "26",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", dur_str,
            "-shortest",
            "-movflags", "+faststart",
            "-threads", "0",
            str(output_video_path)
        ]

        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            detail = (result.stderr or "FFmpeg exited without diagnostic output").strip()
            raise RuntimeError(f"FFmpeg exited with code {result.returncode}: {detail[-1200:]}")

        try:
            if temp_img_path.exists():
                temp_img_path.unlink()
        except Exception:
            pass

        return output_video_path

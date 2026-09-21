import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

def render_burgundy_studio(width=1920, height=1080):
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

def render_deep_nebula(width=1920, height=1080):
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

def render_retrowave_sunset(width=1920, height=1080):
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

def render_midnight_acoustic(width=1920, height=1080):
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

def render_abstract_aurora(width=1920, height=1080):
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

def render_minimal_dark(width=1920, height=1080):
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
    fdraw.line([(frame_pad, height - frame_pad), (frame_pad, height - frame_pad - mark_len)], fill=color, width=2)
    fdraw.line([(width - frame_pad, height - frame_pad), (width - frame_pad - mark_len, height - frame_pad)], fill=color, width=2)
    fdraw.line([(width - frame_pad, height - frame_pad), (width - frame_pad, height - frame_pad - mark_len)], fill=color, width=2)

    fdraw.line([(cx - 15, cy), (cx + 15, cy)], fill=(45, 52, 64), width=1)
    fdraw.line([(cx, cy - 15), (cx, cy + 15)], fill=(45, 52, 64), width=1)
    return img

# 4 New Aesthetic Themes
def render_cyberpunk_neon(width=1920, height=1080):
    img = Image.new("RGB", (width, height), color=(12, 10, 24))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    
    # Electric Cyan & Magenta glowing angled light bars
    cx, cy = width // 2, height // 2
    odraw.line([(0, int(height * 0.3)), (width, int(height * 0.25))], fill=(6, 182, 212, 180), width=16)
    odraw.line([(0, int(height * 0.75)), (width, int(height * 0.7))], fill=(236, 72, 153, 180), width=16)
    odraw.ellipse([cx - 300, cy - 250, cx + 300, cy + 250], fill=(139, 92, 246, 110))
    overlay = overlay.filter(ImageFilter.GaussianBlur(60))
    img.paste(overlay, (0, 0), overlay)

    draw = ImageDraw.Draw(img)
    # Fine digital circuit grid
    for x in range(0, width, 120):
        draw.line([(x, 0), (x, height)], fill=(25, 24, 45), width=1)
    for y in range(0, height, 120):
        draw.line([(0, y), (width, y)], fill=(25, 24, 45), width=1)
    return img

def render_golden_hour(width=1920, height=1080):
    img = Image.new("RGB", (width, height), color=(26, 16, 10))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    cx, cy = width // 2, int(height * 0.4)
    # Warm amber / gold sunset glow
    odraw.ellipse([cx - int(width*0.3), cy - int(height*0.3), cx + int(width*0.3), cy + int(height*0.3)], fill=(245, 158, 11, 200))
    odraw.ellipse([cx - int(width*0.16), cy - int(height*0.16), cx + int(width*0.16), cy + int(height*0.16)], fill=(251, 191, 36, 170))
    overlay = overlay.filter(ImageFilter.GaussianBlur(85))
    img.paste(overlay, (0, 0), overlay)

    # Soft golden bokeh particles
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

def render_velvet_lounge(width=1920, height=1080):
    img = Image.new("RGB", (width, height), color=(10, 14, 28))
    # Royal sapphire & deep indigo velvet spotlight
    cx, cy = width // 2, int(height * 0.45)
    spot = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(spot)
    sdraw.ellipse([cx - int(width*0.28), cy - int(height*0.3), cx + int(width*0.28), cy + int(height*0.3)], fill=(30, 58, 138, 220))
    sdraw.ellipse([cx - int(width*0.14), cy - int(height*0.16), cx + int(width*0.14), cy + int(height*0.16)], fill=(59, 130, 246, 140))
    sdraw.polygon([(cx - 70, 0), (cx + 70, 0), (cx + int(width*0.3), height), (cx - int(width*0.3), height)], fill=(37, 99, 235, 60))
    spot = spot.filter(ImageFilter.GaussianBlur(80))
    img.paste(spot, (0, 0), spot)

    # Velvet curtain vertical ripple folds
    c_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(c_layer)
    for x in range(0, width, 55):
        alpha = int(40 + math.sin(x * 0.1) * 25)
        cdraw.rectangle([x, 0, x + 28, height], fill=(15, 23, 42, alpha))
    c_layer = c_layer.filter(ImageFilter.GaussianBlur(12))
    img.paste(c_layer, (0, 0), c_layer)
    return img

def render_lofi_chill(width=1920, height=1080):
    img = Image.new("RGB", (width, height), color=(22, 16, 26))
    cx, cy = width // 2, height // 2
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    # Lavender / dusty rose warmth
    odraw.ellipse([cx - int(width*0.28), cy - int(height*0.28), cx + int(width*0.28), cy + int(height*0.28)], fill=(168, 85, 247, 120))
    odraw.ellipse([cx - int(width*0.16), cy - int(height*0.16), cx + int(width*0.16), cy + int(height*0.16)], fill=(244, 114, 182, 110))
    overlay = overlay.filter(ImageFilter.GaussianBlur(90))
    img.paste(overlay, (0, 0), overlay)

    # Subtle horizontal CRT / tape lines
    t_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(t_layer)
    for y in range(0, height, 8):
        tdraw.line([(0, y), (width, y)], fill=(10, 8, 14, 45), width=1)
    img.paste(t_layer, (0, 0), t_layer)
    return img

TEMPLATES = {
    "burgundy_studio": render_burgundy_studio,
    "deep_nebula": render_deep_nebula,
    "retrowave_sunset": render_retrowave_sunset,
    "midnight_acoustic": render_midnight_acoustic,
    "abstract_aurora": render_abstract_aurora,
    "minimal_dark": render_minimal_dark,
    "cyberpunk_neon": render_cyberpunk_neon,
    "golden_hour": render_golden_hour,
    "velvet_lounge": render_velvet_lounge,
    "lofi_chill": render_lofi_chill
}

if __name__ == "__main__":
    out_dir = Path("static/img/templates")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, fn in TEMPLATES.items():
        img = fn(width=640, height=360)
        p = out_dir / f"{name}.png"
        img.save(p, "PNG", optimize=True)
        print(f"Generated thumbnail: {p} ({img.size})")

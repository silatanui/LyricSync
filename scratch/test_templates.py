import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

def create_burgundy_studio(width=1920, height=1080):
    # Base dark burgundy / slate background
    img = Image.new("RGB", (width, height), color=(24, 6, 14))
    
    # Spotlight layer with Gaussian blur
    spot = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(spot)
    cx, cy = width // 2, int(height * 0.45)
    # Center warm burgundy spotlight
    sdraw.ellipse([cx - 450, cy - 350, cx + 450, cy + 350], fill=(123, 17, 46, 210))
    sdraw.ellipse([cx - 250, cy - 200, cx + 250, cy + 200], fill=(168, 28, 65, 140))
    # Spotlight cone
    sdraw.polygon([(cx - 100, 0), (cx + 100, 0), (cx + 600, height), (cx - 600, height)], fill=(130, 20, 50, 70))
    spot = spot.filter(ImageFilter.GaussianBlur(85))
    img.paste(spot, (0, 0), spot)

    # Subtle acoustic studio vertical slats
    slat_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    slat_draw = ImageDraw.Draw(slat_layer)
    slat_width = 38
    slat_gap = 14
    for x in range(40, width - 40, slat_width + slat_gap):
        slat_draw.rectangle([x, 30, x + slat_width, height - 30], outline=(38, 12, 22, 120), width=1)
        slat_draw.line([(x + 2, 30), (x + 2, height - 30)], fill=(65, 20, 36, 90), width=1)
    img.paste(slat_layer, (0, 0), slat_layer)

    # Soft radial edge vignette
    vig = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vig)
    # Dark outer border
    vdraw.rectangle([0, 0, width, height], fill=(10, 2, 6, 90))
    vdraw.ellipse([width * 0.15, height * 0.1, width * 0.85, height * 0.9], fill=(0, 0, 0, 0))
    vig = vig.filter(ImageFilter.GaussianBlur(100))
    img.paste(vig, (0, 0), vig)

    return img

def create_deep_nebula(width=1920, height=1080):
    # Midnight celestial indigo
    img = Image.new("RGB", (width, height), color=(8, 8, 20))
    cx, cy = width // 2, height // 2

    # Cosmic glowing nebulas with Gaussian blur
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Nebula clusters
    draw.ellipse([cx - 400, cy - 280, cx + 350, cy + 260], fill=(65, 22, 110, 180))
    draw.ellipse([cx - 200, cy - 150, cx + 180, cy + 140], fill=(105, 40, 160, 150))
    draw.ellipse([width * 0.2 - 200, height * 0.35 - 160, width * 0.2 + 220, height * 0.35 + 180], fill=(22, 60, 125, 160))
    draw.ellipse([width * 0.82 - 240, height * 0.68 - 200, width * 0.82 + 240, height * 0.68 + 200], fill=(120, 30, 95, 150))
    
    overlay = overlay.filter(ImageFilter.GaussianBlur(90))
    img.paste(overlay, (0, 0), overlay)

    # Starfield dots
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

def create_retrowave_sunset(width=1920, height=1080):
    img = Image.new("RGB", (width, height), color=(15, 8, 30))
    draw = ImageDraw.Draw(img)
    horizon_y = int(height * 0.62)

    # Sky gradient: deep purple down to dusk magenta/amber
    for y in range(horizon_y):
        prog = y / horizon_y
        r = int(20 + 175 * (prog ** 1.4))
        g = int(10 + 40 * (prog ** 1.8))
        b = int(35 + 85 * (1.0 - prog))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Giant glowing synth sun on horizon
    cx = width // 2
    sun_r = 180
    sun_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(sun_overlay)
    sdraw.ellipse([cx - sun_r, horizon_y - sun_r, cx + sun_r, horizon_y + sun_r], fill=(255, 140, 50, 230))
    
    # Sun horizontal slice blinds
    for slice_y in range(horizon_y - sun_r + 50, horizon_y, 14):
        sdraw.rectangle([cx - sun_r - 10, slice_y, cx + sun_r + 10, slice_y + 4], fill=(15, 8, 30, 255))
    img.paste(sun_overlay, (0, 0), sun_overlay)

    # Floor: dark magenta-black
    draw.rectangle([0, horizon_y, width, height], fill=(12, 5, 20))

    # Perspective Grid Lines on floor
    # Horizon line
    draw.line([(0, horizon_y), (width, horizon_y)], fill=(245, 60, 140), width=3)
    
    # Vanishing perspective lines
    num_lines = 24
    for i in range(-num_lines, num_lines + 1):
        target_x = cx + i * 85
        draw.line([(cx, horizon_y), (target_x, height)], fill=(180, 30, 110), width=2)

    # Horizontal floor grid lines (exponential spacing)
    y = horizon_y + 12
    step = 8
    while y < height:
        draw.line([(0, int(y)), (width, int(y))], fill=(160, 25, 95), width=1)
        step = int(step * 1.32)
        y += step

    return img

def create_midnight_acoustic(width=1920, height=1080):
    # Charcoal slate with warm studio paneling
    img = Image.new("RGB", (width, height), color=(20, 22, 26))
    draw = ImageDraw.Draw(img)

    # Wood slat texture & warm ambient panels
    panel_w = 48
    gap = 12
    for x in range(40, width - 40, panel_w + gap):
        # Subtle warm wood tone: charcoal brown (35, 32, 30)
        draw.rectangle([x, 60, x + panel_w, height - 60], fill=(28, 26, 25), outline=(42, 38, 36), width=1)
        # Slat highlight edge
        draw.line([(x + 1, 60), (x + 1, height - 60)], fill=(52, 46, 42), width=1)

    # Top-center warm downlight spotlight
    cx = width // 2
    light_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(light_overlay)
    for r in range(700, 0, -25):
        alpha = int((1.0 - (r / 700.0)) ** 1.8 * 65)
        ldraw.ellipse([cx - r, -100, cx + r, r * 1.1], fill=(220, 180, 130, alpha))
    img.paste(light_overlay, (0, 0), light_overlay)

    # Vinyl record grooves watermark in top-right
    vr_x, vr_y = int(width * 0.85), int(height * 0.2)
    vinyl_draw = ImageDraw.Draw(img)
    for gr in range(40, 360, 20):
        vinyl_draw.ellipse([vr_x - gr, vr_y - gr, vr_x + gr, vr_y + gr], outline=(38, 40, 46), width=1)

    return img

def create_abstract_aurora(width=1920, height=1080):
    # Deep emerald & sapphire tones
    img = Image.new("RGB", (width, height), color=(8, 22, 24))
    draw = ImageDraw.Draw(img)

    # Smooth undulating sine curve aurora ribbons
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
        # Draw thick ribbon by offsetting
        for w in range(-c["width"] // 2, c["width"] // 2, 4):
            shifted = [(px, py + w) for px, py in pts]
            alpha = int(c["color"][3] * (1.0 - abs(w) / (c["width"] / 2)))
            odraw.line(shifted, fill=(c["color"][0], c["color"][1], c["color"][2], alpha), width=4)

    img.paste(overlay, (0, 0), overlay)
    return img

def create_minimal_dark(width=1920, height=1080):
    # Ultra-clean carbon graphite vignette with technical crosshairs
    img = Image.new("RGB", (width, height), color=(18, 20, 24))
    draw = ImageDraw.Draw(img)

    # Center soft radial illumination
    cx, cy = width // 2, height // 2
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    max_r = int(math.hypot(cx, cy))
    for r in range(max_r, 0, -30):
        factor = 1.0 - (r / max_r)
        shade = int(18 + 22 * (factor ** 2.0))
        odraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(shade, shade + 3, shade + 8, int(255 * (1.0 - factor * 0.5))))
    img.paste(overlay, (0, 0), overlay)

    # Elegant corner crosshairs & frame
    fdraw = ImageDraw.Draw(img)
    frame_pad = 60
    color = (60, 68, 80)
    # Corner marks (L shapes)
    mark_len = 30
    # Top-Left
    fdraw.line([(frame_pad, frame_pad), (frame_pad + mark_len, frame_pad)], fill=color, width=2)
    fdraw.line([(frame_pad, frame_pad), (frame_pad, frame_pad + mark_len)], fill=color, width=2)
    # Top-Right
    fdraw.line([(width - frame_pad, frame_pad), (width - frame_pad - mark_len, frame_pad)], fill=color, width=2)
    fdraw.line([(width - frame_pad, frame_pad), (width - frame_pad, frame_pad + mark_len)], fill=color, width=2)
    # Bottom-Left
    fdraw.line([(frame_pad, height - frame_pad), (frame_pad + mark_len, height - frame_pad)], fill=color, width=2)
    fdraw.line([(frame_pad, height - frame_pad), (frame_pad, height - frame_pad - mark_len)], fill=color, width=2)
    # Bottom-Right
    fdraw.line([(width - frame_pad, height - frame_pad), (width - frame_pad - mark_len, height - frame_pad)], fill=color, width=2)
    fdraw.line([(width - frame_pad, height - frame_pad), (width - frame_pad, height - frame_pad - mark_len)], fill=color, width=2)

    # Center subtle tick
    fdraw.line([(cx - 15, cy), (cx + 15, cy)], fill=(45, 52, 64), width=1)
    fdraw.line([(cx, cy - 15), (cx, cy + 15)], fill=(45, 52, 64), width=1)

    return img

if __name__ == "__main__":
    out_dir = Path("scratch/template_previews")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    templates = {
        "burgundy_studio": create_burgundy_studio,
        "deep_nebula": create_deep_nebula,
        "retrowave_sunset": create_retrowave_sunset,
        "midnight_acoustic": create_midnight_acoustic,
        "abstract_aurora": create_abstract_aurora,
        "minimal_dark": create_minimal_dark
    }

    for name, fn in templates.items():
        img = fn()
        p = out_dir / f"{name}.png"
        img.save(p)
        print(f"Generated {name} at {p} ({img.size})")

"""Studio theme catalog: procedural looks, photo plates, and motion video beds."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# style: spotlight|nebula|horizon|acoustic|aurora|minimal|neon|golden|lounge|grain|paper|photo
# media_type: image | video
# motion: visualizer | starfield | waves | grid | pulse | still
# asset: optional static/img/themes/... photographic plate


def _t(
    id_: str,
    name: str,
    tagline: str,
    color: str,
    moods: List[str],
    style: str,
    colors: Dict[str, str],
    *,
    media_type: str = "image",
    motion: str = "still",
    asset: str | None = None,
    extras: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if media_type == "video":
        resolved_motion = motion if motion not in (None, "", "still") else "kenburns"
    else:
        resolved_motion = "still"
    thumb = f"/static/{asset}" if asset else f"/api/projects/templates/preview/{id_}"
    return {
        "id": id_,
        "name": name,
        "tagline": tagline,
        "preview_color": color,
        "thumbnail": thumb,
        "moods": moods,
        "media_type": media_type,
        "motion": resolved_motion,
        "style": style,
        "colors": colors,
        "asset": asset,
        "extras": extras or {},
    }


THEME_CATALOG: List[Dict[str, Any]] = [
    # —— AI lyric scene (generated per project from title + lyrics) ——
    _t(
        "ai_lyric_scene",
        "AI Lyric Scene",
        "Custom backdrop imagined from your song lyrics",
        "#0EA5E9",
        ["cinematic", "dreamy", "ai", "warm", "cool"],
        "aurora",
        {"base": "#0B1220", "wave1": "#0EA5E9", "wave2": "#6366F1", "accent": "#E0F2FE"},
        extras={"ai": True},
    ),

    # —— Legacy favorites (kept ids) ——
    _t("burgundy_studio", "Burgundy Studio", "Luxury acoustic spotlight vignette", "#7B112E",
       ["warm", "stage", "romantic", "worship"], "spotlight",
       {"base": "#18060E", "spot": "#7B112E", "glow": "#A81C41", "accent": "#E8B4C0"}),
    _t("deep_nebula", "Deep Nebula", "Cosmic indigo celestial starfield", "#4A154B",
       ["dreamy", "dark", "cinematic", "cool"], "nebula",
       {"base": "#12081C", "mid": "#2B1240", "spot": "#4A154B", "accent": "#C4B5FD"},
       extras={"stars": True}),
    _t("retrowave_sunset", "Retrowave Dusk", "80s synth horizon & neon grid", "#BE185D",
       ["retro", "energetic", "neon", "warm"], "horizon",
       {"top": "#1E1B4B", "mid": "#BE185D", "bottom": "#F97316", "accent": "#22D3EE", "grid": "#F472B6"},
       extras={"grid": True}),
    _t("midnight_acoustic", "Midnight Acoustic", "Charcoal studio wood & warm vinyl", "#334155",
       ["chill", "warm", "minimal", "worship"], "acoustic",
       {"base": "#0F172A", "slat": "#1E293B", "accent": "#F59E0B", "glow": "#78350F"}),
    _t("abstract_aurora", "Abstract Aurora", "Emerald ambient harmonic waves", "#059669",
       ["dreamy", "cool", "nature", "chill"], "aurora",
       {"base": "#022C22", "wave1": "#059669", "wave2": "#34D399", "accent": "#A7F3D0"}),
    _t("minimal_dark", "Minimal Graphite", "Dark carbon vignette with framing marks", "#1E293B",
       ["minimal", "dark", "cinematic"], "minimal",
       {"base": "#0B1220", "frame": "#334155", "accent": "#94A3B8"}),
    _t("cyberpunk_neon", "Cyberpunk Neon", "Electric cyan & magenta lasers", "#06B6D4",
       ["neon", "energetic", "dark", "retro"], "neon",
       {"base": "#020617", "cyan": "#06B6D4", "magenta": "#E11D48", "accent": "#A5F3FC"}),
    _t("golden_hour", "Golden Hour", "Amber sunset warmth & soft dust", "#F59E0B",
       ["warm", "romantic", "cinematic", "chill"], "golden",
       {"base": "#1C1006", "sun": "#F59E0B", "glow": "#FDBA74", "accent": "#FEF3C7"},
       extras={"bokeh": True}),
    _t("velvet_lounge", "Velvet Lounge", "Royal sapphire stage spotlight", "#1D4ED8",
       ["stage", "cool", "romantic", "dark"], "lounge",
       {"base": "#020617", "spot": "#1D4ED8", "glow": "#60A5FA", "accent": "#DBEAFE"}),
    _t("lofi_chill", "Lo-Fi Chill", "Lavender pastel warmth with tape grain", "#A855F7",
       ["chill", "dreamy", "warm", "retro"], "grain",
       {"base": "#1E1030", "wash": "#A855F7", "soft": "#F0ABFC", "accent": "#FDF4FF"},
       extras={"grain": True}),
    _t("emerald_stage", "Emerald Stage", "Deep green concert wash", "#166534",
       ["stage", "worship", "cool", "nature"], "spotlight",
       {"base": "#052E16", "spot": "#166534", "glow": "#22C55E", "accent": "#BBF7D0"}),
    _t("rose_film", "Rose Film", "Cinematic rose and shadow", "#9F1239",
       ["romantic", "cinematic", "warm", "dark"], "horizon",
       {"top": "#1C0610", "mid": "#9F1239", "bottom": "#450A0A", "accent": "#FDA4AF", "grid": "#BE123C"}),
    _t("ocean_pulse", "Ocean Pulse", "Blue motion with cool highlights", "#0369A1",
       ["cool", "chill", "dreamy", "energetic"], "aurora",
       {"base": "#082F49", "wave1": "#0369A1", "wave2": "#38BDF8", "accent": "#E0F2FE"}),
    _t("paper_moon", "Paper Moon", "Warm editorial midnight texture", "#713F12",
       ["warm", "minimal", "cinematic", "worship"], "paper",
       {"base": "#1C1408", "wash": "#713F12", "accent": "#FDE68A", "line": "#A16207"}),

    # —— New catalog ——
    _t("crimson_altar", "Crimson Altar", "Deep worship red with soft haze", "#991B1B",
       ["worship", "warm", "stage", "romantic"], "spotlight",
       {"base": "#1A0505", "spot": "#991B1B", "glow": "#DC2626", "accent": "#FECACA"}),
    _t("sanctuary_gold", "Sanctuary Gold", "Quiet gold light for gospel ballads", "#B45309",
       ["worship", "warm", "chill", "minimal"], "golden",
       {"base": "#1A1004", "sun": "#B45309", "glow": "#FBBF24", "accent": "#FEF3C7"}),
    _t("halo_white", "Halo White", "Soft white radiance on charcoal", "#E5E7EB",
       ["worship", "minimal", "dreamy", "cool"], "spotlight",
       {"base": "#111827", "spot": "#9CA3AF", "glow": "#F9FAFB", "accent": "#FFFFFF"}),
    _t("olive_prayer", "Olive Prayer", "Muted olive chapel atmosphere", "#3F6212",
       ["worship", "nature", "chill", "warm"], "acoustic",
       {"base": "#14210A", "slat": "#365314", "accent": "#A3E635", "glow": "#3F6212"}),
    _t("indigo_vespers", "Indigo Vespers", "Night-blue contemplative wash", "#312E81",
       ["worship", "dark", "cool", "dreamy"], "lounge",
       {"base": "#0B1026", "spot": "#312E81", "glow": "#6366F1", "accent": "#C7D2FE"}),

    _t("sakura_dusk", "Sakura Dusk", "Blush pink evening petals of light", "#DB2777",
       ["romantic", "warm", "dreamy", "chill"], "grain",
       {"base": "#2A0A18", "wash": "#DB2777", "soft": "#F9A8D4", "accent": "#FDF2F8"},
       extras={"grain": True, "bokeh": True}),
    _t("candlelit", "Candlelit", "Intimate amber candle pockets", "#D97706",
       ["romantic", "warm", "chill", "cinematic"], "spotlight",
       {"base": "#1A0E04", "spot": "#B45309", "glow": "#F59E0B", "accent": "#FEF3C7"},
       extras={"bokeh": True}),
    _t("blush_noir", "Blush Noir", "Soft rose over deep black", "#BE123C",
       ["romantic", "dark", "cinematic", "minimal"], "minimal",
       {"base": "#0C0408", "frame": "#4C0519", "accent": "#FB7185"}),
    _t("champagne_room", "Champagne Room", "Pale gold lounge shimmer", "#CA8A04",
       ["romantic", "warm", "stage", "chill"], "lounge",
       {"base": "#1C1608", "spot": "#A16207", "glow": "#EAB308", "accent": "#FEF9C3"}),

    _t("arctic_mist", "Arctic Mist", "Icy blue fog and pale light", "#38BDF8",
       ["cool", "minimal", "dreamy", "chill"], "aurora",
       {"base": "#0C1929", "wave1": "#0EA5E9", "wave2": "#7DD3FC", "accent": "#E0F2FE"}),
    _t("glacier_edge", "Glacier Edge", "Cold steel blue ridges", "#0284C7",
       ["cool", "cinematic", "dark", "minimal"], "minimal",
       {"base": "#020617", "frame": "#0C4A6E", "accent": "#7DD3FC"}),
    _t("teal_tide", "Teal Tide", "Rolling teal water gradients", "#0D9488",
       ["cool", "nature", "chill", "dreamy"], "aurora",
       {"base": "#042F2E", "wave1": "#0D9488", "wave2": "#2DD4BF", "accent": "#CCFBF1"}),
    _t("midnight_harbor", "Midnight Harbor", "Navy docks under sodium lamps", "#1E3A8A",
       ["cool", "cinematic", "dark", "chill"], "acoustic",
       {"base": "#020617", "slat": "#1E3A8A", "accent": "#FBBF24", "glow": "#312E81"}),

    _t("forest_canopy", "Forest Canopy", "Deep green leaf-shadow light", "#14532D",
       ["nature", "chill", "cool", "worship"], "aurora",
       {"base": "#052E16", "wave1": "#166534", "wave2": "#4ADE80", "accent": "#DCFCE7"}),
    _t("moss_garden", "Moss Garden", "Soft moss and morning dew", "#3F6212",
       ["nature", "chill", "warm", "minimal"], "grain",
       {"base": "#1A2E05", "wash": "#4D7C0F", "soft": "#A3E635", "accent": "#ECFCCB"},
       extras={"grain": True}),
    _t("desert_bloom", "Desert Bloom", "Sandstone dusk with coral heat", "#C2410C",
       ["nature", "warm", "cinematic", "romantic"], "horizon",
       {"top": "#1C1008", "mid": "#C2410C", "bottom": "#FDBA74", "accent": "#FFEDD5", "grid": "#9A3412"}),
    _t("savanna_dusk", "Savanna Dusk", "Wide amber plains under violet sky", "#B45309",
       ["nature", "warm", "cinematic", "chill"], "horizon",
       {"top": "#2E1065", "mid": "#B45309", "bottom": "#FCD34D", "accent": "#FEF3C7", "grid": "#78350F"}),

    _t("voltage_pink", "Voltage Pink", "Hot pink laser night", "#EC4899",
       ["neon", "energetic", "dark", "retro"], "neon",
       {"base": "#19010F", "cyan": "#22D3EE", "magenta": "#EC4899", "accent": "#FCE7F3"}),
    _t("laser_lime", "Laser Lime", "Acid lime neon on black", "#84CC16",
       ["neon", "energetic", "dark"], "neon",
       {"base": "#0A1202", "cyan": "#A3E635", "magenta": "#22D3EE", "accent": "#ECFCCB"}),
    _t("circuit_blue", "Circuit Blue", "Tech blue grid pulse", "#2563EB",
       ["neon", "energetic", "cool", "retro"], "horizon",
       {"top": "#020617", "mid": "#1D4ED8", "bottom": "#0F172A", "accent": "#93C5FD", "grid": "#38BDF8"},
       extras={"grid": True}),
    _t("toxic_orchid", "Toxic Orchid", "Purple-green club haze", "#7C3AED",
       ["neon", "dark", "energetic", "dreamy"], "nebula",
       {"base": "#0F051A", "mid": "#5B21B6", "spot": "#A21CAF", "accent": "#86EFAC"},
       extras={"stars": True}),

    _t("vinyl_sepia", "Vinyl Sepia", "Warm tape-room sepia grain", "#92400E",
       ["retro", "warm", "chill", "cinematic"], "grain",
       {"base": "#1C1208", "wash": "#92400E", "soft": "#D97706", "accent": "#FEF3C7"},
       extras={"grain": True}),
    _t("vhs_night", "VHS Night", "Nostalgic blue-magenta scanlines", "#7C3AED",
       ["retro", "neon", "dark", "chill"], "neon",
       {"base": "#0B0614", "cyan": "#67E8F9", "magenta": "#C084FC", "accent": "#E9D5FF"},
       extras={"grain": True}),
    _t("arcade_dusk", "Arcade Dusk", "Sunset cabinets & purple haze", "#C026D3",
       ["retro", "energetic", "neon", "warm"], "horizon",
       {"top": "#3B0764", "mid": "#C026D3", "bottom": "#FB923C", "accent": "#F5D0FE", "grid": "#E879F9"}),
    _t("cassette_cream", "Cassette Cream", "Soft cream lo-fi bedroom light", "#D6D3D1",
       ["retro", "chill", "warm", "minimal"], "paper",
       {"base": "#1C1917", "wash": "#78716C", "accent": "#FAFAF9", "line": "#A8A29E"}),

    _t("storm_slate", "Storm Slate", "Heavy grey stormfront", "#475569",
       ["cinematic", "dark", "cool", "minimal"], "minimal",
       {"base": "#0F172A", "frame": "#334155", "accent": "#CBD5E1"}),
    _t("noir_alley", "Noir Alley", "Hard contrast street noir", "#111827",
       ["cinematic", "dark", "cool"], "spotlight",
       {"base": "#030712", "spot": "#374151", "glow": "#9CA3AF", "accent": "#F3F4F6"}),
    _t("smoke_room", "Smoke Room", "Soft grey smoke curtains", "#6B7280",
       ["cinematic", "dark", "chill", "romantic"], "aurora",
       {"base": "#111827", "wave1": "#4B5563", "wave2": "#9CA3AF", "accent": "#E5E7EB"}),
    _t("ember_ash", "Ember Ash", "Dying embers over ash black", "#9A3412",
       ["cinematic", "warm", "dark", "romantic"], "golden",
       {"base": "#120805", "sun": "#9A3412", "glow": "#EA580C", "accent": "#FED7AA"},
       extras={"bokeh": True}),

    _t("pulse_red", "Pulse Red", "High-energy stage red", "#DC2626",
       ["energetic", "stage", "warm", "dark"], "spotlight",
       {"base": "#1A0505", "spot": "#DC2626", "glow": "#F87171", "accent": "#FEE2E2"}),
    _t("stadium_lights", "Stadium Lights", "White beams over night field", "#F8FAFC",
       ["energetic", "stage", "cool", "cinematic"], "spotlight",
       {"base": "#020617", "spot": "#94A3B8", "glow": "#F1F5F9", "accent": "#FFFFFF"}),
    _t("bass_violet", "Bass Violet", "Club violet low-end glow", "#6D28D9",
       ["energetic", "neon", "dark", "stage"], "lounge",
       {"base": "#12031F", "spot": "#6D28D9", "glow": "#A78BFA", "accent": "#EDE9FE"}),
    _t("sunrise_run", "Sunrise Run", "Bright dawn for uptempo tracks", "#FB923C",
       ["energetic", "warm", "nature", "chill"], "horizon",
       {"top": "#0C4A6E", "mid": "#FB923C", "bottom": "#FDE68A", "accent": "#FFFBEB", "grid": "#EA580C"}),

    _t("soft_linen", "Soft Linen", "Clean light fabric wash", "#F5F5F4",
       ["minimal", "warm", "chill", "worship"], "paper",
       {"base": "#1C1917", "wash": "#A8A29E", "accent": "#FAFAF9", "line": "#D6D3D1"}),
    _t("ink_sketch", "Ink Sketch", "Near-black with thin white marks", "#0A0A0A",
       ["minimal", "dark", "cinematic"], "minimal",
       {"base": "#050505", "frame": "#262626", "accent": "#E5E5E5"}),
    _t("porcelain_blue", "Porcelain Blue", "Pale porcelain cool calm", "#BAE6FD",
       ["minimal", "cool", "chill", "dreamy"], "minimal",
       {"base": "#0C1929", "frame": "#0369A1", "accent": "#E0F2FE"}),
    _t(" Quiet_sand", "Quiet Sand", "Muted sand studio floor", "#D6D3D1",
       ["minimal", "warm", "chill"], "acoustic",
       {"base": "#1C1917", "slat": "#57534E", "accent": "#E7E5E4", "glow": "#78716C"}),

    _t("dream_fog", "Dream Fog", "Lavender fog banks in motion", "#C4B5FD",
       ["dreamy", "chill", "cool", "romantic"], "aurora",
       {"base": "#1E1B4B", "wave1": "#8B5CF6", "wave2": "#C4B5FD", "accent": "#EDE9FE"}),
    _t("starlit_meadow", "Starlit Meadow", "Soft green night under stars", "#4ADE80",
       ["dreamy", "nature", "cool", "chill"], "nebula",
       {"base": "#052E16", "mid": "#14532D", "spot": "#166534", "accent": "#BBF7D0"},
       extras={"stars": True}),
    _t("cloud_chapel", "Cloud Chapel", "Soft cloud whites over blue", "#93C5FD",
       ["dreamy", "worship", "cool", "chill"], "spotlight",
       {"base": "#0F172A", "spot": "#60A5FA", "glow": "#DBEAFE", "accent": "#F8FAFC"}),
    _t("moon_river", "Moon River", "Silver moonlight on deep water", "#CBD5E1",
       ["dreamy", "cool", "romantic", "cinematic"], "aurora",
       {"base": "#020617", "wave1": "#334155", "wave2": "#94A3B8", "accent": "#F1F5F9"}),

    # —— Photo plates & creative motion (from real-world / worship references) ——
    _t("city_vespers", "City Vespers", "Cathedral skyline under a painted sunset", "#F97316",
       ["worship", "cinematic", "warm", "real"], "photo",
       {"base": "#1C0A04", "accent": "#FDBA74"},
       asset="img/themes/city_vespers.jpg"),
    _t("twilight_covenant", "Twilight Covenant", "Joined hands under a crescent dusk sky", "#0F766E",
       ["romantic", "worship", "dreamy", "real"], "photo",
       {"base": "#042F2E", "accent": "#FDBA74"},
       asset="img/themes/twilight_hands.png"),
    _t("calvary_sunrise", "Calvary Sunrise", "Cross on the hill with golden sun rays", "#F59E0B",
       ["worship", "cinematic", "warm", "real"], "photo",
       {"base": "#1C1006", "accent": "#FDE68A"},
       asset="img/themes/cross_sunrise.png"),
    _t("starlit_peaks", "Starlit Peaks", "Snow mountains under a deep star field", "#1E3A8A",
       ["worship", "cool", "dreamy", "nature", "real"], "photo",
       {"base": "#020617", "accent": "#DBEAFE"},
       asset="img/themes/starlit_peaks.png"),
    _t("cathedral_glow", "Cathedral Glow", "Warm city vespers still for lyric cards", "#EA580C",
       ["worship", "cinematic", "warm", "real"], "photo",
       {"base": "#1C0A04", "accent": "#FDBA74"},
       asset="img/themes/city_vespers.jpg"),
    _t("promise_dusk", "Promise Dusk", "Silhouette devotion under the crescent", "#134E4A",
       ["romantic", "worship", "real", "chill"], "photo",
       {"base": "#042F2E", "accent": "#FDBA74"},
       asset="img/themes/twilight_hands.png"),
    _t("hillside_cross", "Hillside Cross", "Still of the sunrise calvary scene", "#D97706",
       ["worship", "cinematic", "warm", "real"], "photo",
       {"base": "#1C1006", "accent": "#FDE68A"},
       asset="img/themes/cross_sunrise.png"),
    _t("alpine_psalm", "Alpine Psalm", "Quiet night peaks for contemplative songs", "#1D4ED8",
       ["worship", "cool", "nature", "real", "chill"], "photo",
       {"base": "#020617", "accent": "#DBEAFE"},
       asset="img/themes/starlit_peaks.png"),

    # —— Serious video themes (animated frames: visualizer / pulse / starfield / waves) ——
    _t("gospel_spectrum", "Gospel Spectrum", "Royal purple stage with live EQ bars", "#6D28D9",
       ["worship", "energetic", "stage", "visualizer"], "horizon",
       {"top": "#2E1065", "mid": "#7C3AED", "bottom": "#9F1239", "accent": "#FFFFFF", "grid": "#C4B5FD"},
       media_type="video", motion="visualizer",
       extras={"bars": 88, "bar_color": "#FFFFFF", "clear_lower": True}),
    _t("sanctuary_wave", "Sanctuary Wave", "Gold worship wash with rising spectrum bars", "#B45309",
       ["worship", "warm", "chill", "visualizer"], "golden",
       {"base": "#1A1004", "sun": "#B45309", "glow": "#FBBF24", "accent": "#FFFFFF"},
       media_type="video", motion="visualizer",
       extras={"bars": 72, "bar_color": "#FEF3C7", "clear_lower": True}),
    _t("mercy_bars", "Mercy Bars", "Deep indigo stage with dancing white meters", "#312E81",
       ["worship", "stage", "visualizer", "dark"], "spotlight",
       {"base": "#0B1026", "spot": "#312E81", "glow": "#6366F1", "accent": "#FFFFFF"},
       media_type="video", motion="visualizer",
       extras={"bars": 96, "bar_color": "#E0E7FF", "clear_lower": True}),
    _t("neon_equalizer", "Neon Equalizer", "Cyan-magenta club EQ bouncing hard", "#06B6D4",
       ["neon", "energetic", "dark", "visualizer", "stage"], "neon",
       {"base": "#020617", "cyan": "#06B6D4", "magenta": "#E11D48", "accent": "#A5F3FC"},
       media_type="video", motion="visualizer",
       extras={"bars": 100, "bar_color": "#67E8F9", "clear_lower": True}),
    _t("bass_reactor", "Bass Reactor", "Crimson low-end reactor bars", "#DC2626",
       ["energetic", "stage", "dark", "visualizer", "warm"], "spotlight",
       {"base": "#140303", "spot": "#991B1B", "glow": "#EF4444", "accent": "#FECACA"},
       media_type="video", motion="visualizer",
       extras={"bars": 84, "bar_color": "#FCA5A5", "clear_lower": True}),
    _t("ocean_meters", "Ocean Meters", "Teal tide with cool spectrum bars", "#0D9488",
       ["cool", "chill", "visualizer", "nature"], "aurora",
       {"base": "#042F2E", "wave1": "#0D9488", "wave2": "#2DD4BF", "accent": "#CCFBF1"},
       media_type="video", motion="visualizer",
       extras={"bars": 76, "bar_color": "#99F6E4", "clear_lower": True}),
    _t("violet_meters", "Violet Meters", "Club violet with bright lavender bars", "#7C3AED",
       ["neon", "energetic", "dark", "visualizer"], "lounge",
       {"base": "#12031F", "spot": "#6D28D9", "glow": "#A78BFA", "accent": "#EDE9FE"},
       media_type="video", motion="visualizer",
       extras={"bars": 90, "bar_color": "#DDD6FE", "clear_lower": True}),
    _t("starfall_night", "Starfall Night", "Twinkling cosmic starfield in motion", "#4A154B",
       ["dreamy", "dark", "cinematic", "cool"], "nebula",
       {"base": "#12081C", "mid": "#2B1240", "spot": "#4A154B", "accent": "#C4B5FD"},
       media_type="video", motion="starfield",
       extras={"stars": True}),
    _t("aurora_drift", "Aurora Drift", "Moving emerald aurora bands", "#059669",
       ["dreamy", "cool", "nature", "chill"], "aurora",
       {"base": "#022C22", "wave1": "#059669", "wave2": "#34D399", "accent": "#A7F3D0"},
       media_type="video", motion="waves"),
    _t("grid_runner", "Grid Runner", "Scrolling synthwave neon grid", "#BE185D",
       ["retro", "energetic", "neon", "warm"], "horizon",
       {"top": "#1E1B4B", "mid": "#BE185D", "bottom": "#F97316", "accent": "#22D3EE", "grid": "#F472B6"},
       media_type="video", motion="grid",
       extras={"grid": True}),
    _t("halo_pulse", "Halo Pulse", "Soft white radiance that breathes", "#E5E7EB",
       ["worship", "minimal", "dreamy", "cool"], "spotlight",
       {"base": "#111827", "spot": "#9CA3AF", "glow": "#F9FAFB", "accent": "#FFFFFF"},
       media_type="video", motion="pulse"),
    _t("ember_pulse", "Ember Pulse", "Warm ember glow breathing on ash", "#EA580C",
       ["warm", "cinematic", "dark", "romantic"], "golden",
       {"base": "#120805", "sun": "#9A3412", "glow": "#EA580C", "accent": "#FED7AA"},
       media_type="video", motion="pulse",
       extras={"bokeh": True}),

]

# Fix accidental space in id from Quiet Sand
for _theme in THEME_CATALOG:
    if _theme["id"] == " Quiet_sand":
        _theme["id"] = "quiet_sand"
        _theme["thumbnail"] = "/api/projects/templates/preview/quiet_sand"
        break

# Video themes must declare a real animated motion (no silent Ken Burns).
_REAL_MOTION = {"visualizer", "starfield", "waves", "grid", "pulse"}
for _theme in THEME_CATALOG:
    if _theme.get("media_type") == "video" and _theme.get("motion") not in _REAL_MOTION:
        _theme["media_type"] = "image"
        _theme["motion"] = "still"

MOODS = [
    "all", "ai", "worship", "romantic", "chill", "dark", "energetic",
    "cinematic", "retro", "nature", "neon", "warm", "cool",
    "minimal", "stage", "dreamy", "real", "visualizer",
]


def get_theme_catalog() -> List[Dict[str, Any]]:
    return list(THEME_CATALOG)


def get_theme(theme_id: str) -> Optional[Dict[str, Any]]:
    key = (theme_id or "").strip().lower()
    for theme in THEME_CATALOG:
        if theme["id"] == key:
            return theme
    return None


def get_moods() -> List[str]:
    return list(MOODS)


def public_theme_payload(theme: Dict[str, Any]) -> Dict[str, Any]:
    """Strip render-only fields for API clients."""
    motion = theme.get("motion") or "still"
    extras = theme.get("extras") or {}
    return {
        "id": theme["id"],
        "name": theme["name"],
        "tagline": theme.get("tagline", ""),
        "preview_color": theme.get("preview_color", "#334155"),
        "thumbnail": theme.get("thumbnail"),
        "moods": theme.get("moods", []),
        "media_type": theme.get("media_type", "image"),
        "motion": motion,
        "is_video": theme.get("media_type") == "video",
        "is_visualizer": motion == "visualizer",
        "is_motion": motion in {"visualizer", "starfield", "waves", "grid", "pulse"},
        "is_photo": theme.get("style") == "photo" or bool(theme.get("asset")),
        "is_ai": bool(extras.get("ai")) or theme.get("id") == "ai_lyric_scene",
    }

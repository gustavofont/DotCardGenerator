from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import math

# All layout constants below are expressed in *final* 600x840 pixel space.
# Every drawing call multiplies by SS — the whole card is rendered at SSx
# resolution and downsampled with LANCZOS at the end. This is what keeps the
# frame's rounded corners gapless: PIL's rounded_rectangle leaves visible
# notches at width>1 when drawn directly at 1x; supersample-then-antialias
# removes them.
SS = 3
W, H = 600, 840
FRAME = 18
FOOTER_H = 172

INK = (28, 22, 16)
BADGE_BG = (232, 221, 198)
PANEL_BG = (14, 11, 8)

RARITY_STYLE = {
    "COMMON":    {"color": (170, 170, 175), "glow": 0},
    "RARE":      {"color": (70, 140, 230),  "glow": 9},
    "EPIC":      {"color": (168, 70, 230),  "glow": 16},
    "LEGENDARY": {"color": (230, 175, 45),  "glow": 24},
}

VALID_RARITIES = set(RARITY_STYLE.keys())
VALID_TYPES = {"CREATURE", "LAND", "SORCERY", "ARTIFACT"}

_FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/System/Library/Fonts/Supplemental",
]


def _load_font(filename, size):
    for base in _FONT_DIRS:
        path = f"{base}/{filename}"
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def font(size, bold=False):
    name = "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf"
    return _load_font(name, int(size * SS))


def small_font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return _load_font(name, int(size * SS))


# ---------------------------------------------------------------------------
# Type icons — bold, flat silhouettes. Each card type gets the clearest
# single-glyph match:
#   LAND      -> tree     (direct match — lands ARE terrain)
#   SORCERY   -> flame    (dynamic energy/spell reading)
#   ARTIFACT  -> rune     (circular seal — crafted/magical object)
#   CREATURE  -> skull    (living-being/monster shorthand; common in TCGs)
# ---------------------------------------------------------------------------

def draw_tree(draw, cx, cy, s, ink):
    tw = s * 0.18
    draw.rectangle([cx - tw / 2, cy + s * 0.40, cx + tw / 2, cy + s * 0.85], fill=ink)
    draw.polygon([(cx, cy - s * 0.95), (cx - s * 0.42, cy - s * 0.25), (cx + s * 0.42, cy - s * 0.25)], fill=ink)
    draw.polygon([(cx, cy - s * 0.55), (cx - s * 0.58, cy + s * 0.42), (cx + s * 0.58, cy + s * 0.42)], fill=ink)


def draw_flame(draw, cx, cy, s, ink, bg):
    outer = [
        (0, -1.05), (0.40, -0.35), (0.30, 0.05), (0.48, 0.42),
        (0.18, 1.05), (0, 0.80), (-0.18, 1.05), (-0.48, 0.42),
        (-0.30, 0.05), (-0.40, -0.35),
    ]
    draw.polygon([(cx + px * s, cy + py * s) for px, py in outer], fill=ink)
    inner = [
        (0, -0.55), (0.18, -0.05), (0.12, 0.25), (0.20, 0.55),
        (0, 0.80), (-0.20, 0.55), (-0.12, 0.25), (-0.18, -0.05),
    ]
    draw.polygon([(cx + px * s, cy + py * s) for px, py in inner], fill=bg)


def draw_skull(draw, cx, cy, s, ink, bg):
    r = s * 0.58
    draw.ellipse([cx - r, cy - r * 0.95, cx + r, cy + r * 0.68], fill=ink)
    jaw_w = s * 0.58
    draw.rectangle([cx - jaw_w / 2, cy + r * 0.12, cx + jaw_w / 2, cy + r * 0.66], fill=ink)
    eye_r = s * 0.15
    draw.ellipse([cx - s * 0.27 - eye_r, cy - s * 0.04 - eye_r, cx - s * 0.27 + eye_r, cy - s * 0.04 + eye_r], fill=bg)
    draw.ellipse([cx + s * 0.27 - eye_r, cy - s * 0.04 - eye_r, cx + s * 0.27 + eye_r, cy - s * 0.04 + eye_r], fill=bg)
    draw.polygon([(cx, cy + s * 0.06), (cx - s * 0.07, cy + s * 0.22), (cx + s * 0.07, cy + s * 0.22)], fill=bg)
    for i in (-1, 0, 1):
        x = cx + i * s * 0.13
        draw.rectangle([x - s * 0.02, cy + r * 0.32, x + s * 0.02, cy + r * 0.58], fill=bg)


def draw_rune(draw, cx, cy, s, ink, bg):
    r_outer = s * 0.60
    r_inner = s * 0.40
    draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], fill=ink)
    draw.ellipse([cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner], fill=bg)
    r_dot = s * 0.15
    draw.ellipse([cx - r_dot, cy - r_dot, cx + r_dot, cy + r_dot], fill=ink)
    for i in range(8):
        ang = i * (math.pi / 4)
        x1, y1 = cx + math.cos(ang) * r_outer * 1.05, cy + math.sin(ang) * r_outer * 1.05
        x2, y2 = cx + math.cos(ang) * r_outer * 1.35, cy + math.sin(ang) * r_outer * 1.35
        draw.line([x1, y1, x2, y2], fill=ink, width=max(1, int(s * 0.09)))


def draw_type_icon(draw, cx, cy, s, kind, ink=INK, bg=BADGE_BG):
    if kind == "LAND":
        draw_tree(draw, cx, cy, s, ink)
    elif kind == "SORCERY":
        draw_flame(draw, cx, cy, s, ink, bg)
    elif kind == "ARTIFACT":
        draw_rune(draw, cx, cy, s, ink, bg)
    elif kind == "CREATURE":
        draw_skull(draw, cx, cy, s, ink, bg)


def compose_card(art_path, name, card_type, rarity, collection, out_path):
    if card_type not in VALID_TYPES:
        raise ValueError(f"invalid card type '{card_type}' — must be one of {sorted(VALID_TYPES)}")
    if rarity not in VALID_RARITIES:
        raise ValueError(f"invalid rarity '{rarity}' — must be one of {sorted(VALID_RARITIES)}")

    style = RARITY_STYLE[rarity]
    accent = style["color"]

    WS, HS = W * SS, H * SS
    base = Image.new("RGB", (WS, HS), PANEL_BG)

    # Outer glow (skipped for COMMON — glow == 0)
    if style["glow"] > 0:
        glow_layer = Image.new("RGBA", (WS, HS), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow_layer)
        pad = 6 * SS
        gdraw.rounded_rectangle(
            [FRAME * SS - pad, FRAME * SS - pad, WS - FRAME * SS + pad, HS - FRAME * SS + pad],
            radius=24 * SS, fill=(*accent, 160),
        )
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(style["glow"] * SS * 0.6))
        base = Image.alpha_composite(base.convert("RGBA"), glow_layer).convert("RGB")

    draw = ImageDraw.Draw(base, "RGBA")

    # Single clean outer frame — supersampled, so corners stay gapless.
    draw.rounded_rectangle(
        [FRAME * SS, FRAME * SS, WS - FRAME * SS, HS - FRAME * SS],
        radius=20 * SS, outline=accent, width=5 * SS,
    )

    # Art
    art_top, art_bottom = (FRAME + 26) * SS, (H - FRAME - FOOTER_H) * SS
    art_left, art_right = (FRAME + 26) * SS, (W - FRAME - 26) * SS
    art_w, art_h = art_right - art_left, art_bottom - art_top
    art = Image.open(art_path).convert("RGB")
    art_fitted = ImageOps.fit(art, (art_w, art_h), method=Image.LANCZOS, centering=(0.5, 0.35))
    base.paste(art_fitted, (art_left, art_top))
    draw.rectangle([art_left, art_top, art_right, art_bottom], outline=accent, width=3 * SS)

    # Footer
    footer_top = H - FRAME - FOOTER_H
    name_font = font(30, bold=True)
    name_w = draw.textlength(name, font=name_font)
    if name_w > (W - 2 * (FRAME + 20)) * SS:
        name_font = font(24, bold=True)
        name_w = draw.textlength(name, font=name_font)
    draw.text(((WS - name_w) / 2, (footer_top + 14) * SS), name, font=name_font, fill=(240, 232, 214))

    divider_color = (*accent, 140)
    y1 = (footer_top + 58) * SS
    draw.line([(FRAME + 14) * SS, y1, (W - FRAME - 14) * SS, y1], fill=divider_color, width=max(1, SS))

    row_cy = (footer_top + 83) * SS
    badge_r = 15 * SS
    badge_cx = (FRAME + 30) * SS
    draw.ellipse(
        [badge_cx - badge_r, row_cy - badge_r, badge_cx + badge_r, row_cy - badge_r + 2 * badge_r],
        fill=BADGE_BG,
    )
    draw_type_icon(draw, badge_cx, row_cy, badge_r * 0.82, card_type)

    type_font = small_font(16)
    draw.text((badge_cx + badge_r + 10 * SS, row_cy - 9 * SS), card_type.capitalize(), font=type_font, fill=(225, 218, 202))

    rarity_font = small_font(16, bold=True)
    rarity_text = rarity.upper()
    rarity_w = draw.textlength(rarity_text, font=rarity_font)
    draw.text(((W - FRAME - 14) * SS - rarity_w, row_cy - 9 * SS), rarity_text, font=rarity_font, fill=accent)

    y2 = (footer_top + 106) * SS
    draw.line([(FRAME + 14) * SS, y2, (W - FRAME - 14) * SS, y2], fill=divider_color, width=max(1, SS))

    coll_font = small_font(13)
    coll_text = f"Collection: {collection}"
    coll_w = draw.textlength(coll_text, font=coll_font)
    draw.text(((WS - coll_w) / 2, (footer_top + 116) * SS), coll_text, font=coll_font, fill=(150, 142, 128))

    sigil_cy = (footer_top + 150) * SS
    draw_rune(draw, WS / 2, sigil_cy, 9 * SS, accent, PANEL_BG)

    base = base.resize((W, H), Image.LANCZOS)
    base.convert("RGB").save(out_path)
    return out_path

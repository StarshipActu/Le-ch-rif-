"""Génération des visuels 1280x720 (PNG)."""
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).parent
S = 2  # suréchantillonnage pour lisser les bords
W, H = 1280 * S, 720 * S
TZ_PARIS = ZoneInfo("Europe/Paris")
AMBER = (255, 176, 32)
CYAN = (40, 196, 230)
FOOTER = "starbase.texas.gov/beach-road-access"


def font(size, mono=False, bold=True):
    name = ("DejaVuSansMono" if mono else "DejaVuSans") + ("-Bold" if bold else "") + ".ttf"
    return ImageFont.truetype(str(ROOT / "fonts" / name), int(size * S))


_logo = None


def logo():
    """Logo avec le fond blanc extérieur rendu transparent."""
    global _logo
    if _logo is None:
        src = Path(ROOT / "assets" / "logo.webp")
        if not src.exists():
            src = ROOT / "assets" / "logo.png"
        im = Image.open(src).convert("RGBA")
        flat = im.convert("RGB")
        key = (255, 0, 255)
        w, h = flat.size
        for pt in ((1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)):
            ImageDraw.floodfill(flat, pt, key, thresh=40)
        px, out = flat.load(), im.load()
        for y in range(h):
            for x in range(w):
                if px[x, y] == key:
                    out[x, y] = (255, 255, 255, 0)
        _logo = im
    return _logo


def fmt_window(win, tz):
    s, e = win.start.astimezone(tz), win.end.astimezone(tz)
    a, b = f"{s:%d/%m}", f"{e:%d/%m}"
    if a == b:
        return f"{a} · {s:%Hh%M} – {e:%Hh%M}"
    return f"{a} {s:%Hh%M} → {b} {e:%Hh%M}"


def _center_text(d, cx, cy, txt, f, fill):
    tw = d.textlength(txt, font=f)
    bb = f.getbbox(txt)
    d.text((cx - tw / 2, cy - (bb[3] - bb[1]) / 2 - bb[1]), txt, font=f, fill=fill)


def render(path, *, accent, title, subtitle, headline, headline_sub,
           boxes=None, big_status=None, chip=None, window=None):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(8 + 10 * t), int(14 + 16 * t), int(26 + 22 * t)))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).ellipse([W * .55, -H * .5, W * 1.3, H * .5],
                                 fill=tuple(int(v * .22) for v in accent))
    img = ImageChops.add(img, glow.filter(ImageFilter.GaussianBlur(160)))

    def stripes(y0, y1):
        band = Image.new("RGB", (W, y1 - y0), (18, 22, 30))
        bd = ImageDraw.Draw(band)
        step, h = 44 * S, y1 - y0
        for x in range(-h, W + step, step):
            bd.polygon([(x, h), (x + step // 2, h), (x + step // 2 + h, 0), (x + h, 0)], fill=accent)
        img.paste(band, (0, y0))
    stripes(0, 14 * S)
    stripes(H - 14 * S, H)
    d = ImageDraw.Draw(img)

    # icône d'alerte
    cx, cy, r = 100 * S, 100 * S, 52 * S
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)],
              fill=(30, 26, 18), outline=accent, width=5 * S)
    d.rounded_rectangle([cx - 5 * S, cy - 26 * S, cx + 5 * S, cy + 8 * S], radius=3 * S, fill=accent)
    d.ellipse([cx - 6 * S, cy + 16 * S, cx + 6 * S, cy + 28 * S], fill=accent)

    d.text((180 * S, 48 * S), title, font=font(76), fill="white")
    d.text((182 * S, 138 * S), subtitle, font=font(24, mono=True), fill=accent)
    d.line([(44 * S, 186 * S), (1000 * S, 186 * S)], fill=accent, width=3 * S)
    d.text((44 * S, 222 * S), headline, font=font(50, mono=True), fill="white")
    if headline_sub:
        d.text((46 * S, 290 * S), headline_sub, font=font(24, mono=True, bold=False), fill=(170, 178, 190))

    if chip:  # petite pastille EN COURS / À VENIR
        f = font(24, mono=True)
        tw = d.textlength(chip, font=f) / S
        x0 = 1000 - tw - 40
        d.rounded_rectangle([x0 * S, 232 * S, 1000 * S, 282 * S], radius=25 * S, outline=accent, width=3 * S)
        _center_text(d, (x0 + (1000 - x0) / 2) * S, 257 * S, chip, f, accent)

    y = 345
    if boxes:
        d.text((46 * S, y * S), "SENS DE LA FERMETURE", font=font(20, mono=True), fill=accent)
        bw, bh, yb = 420, 84, y + 40
        f = font(32, mono=True)
        for i, txt in enumerate(boxes):
            x = 46 + i * (bw + 120)
            d.rounded_rectangle([x * S, yb * S, (x + bw) * S, (yb + bh) * S], radius=14 * S,
                                fill=(20, 28, 42), outline=(70, 82, 100), width=2 * S)
            _center_text(d, (x + bw / 2) * S, (yb + bh / 2) * S, txt, f, "white")
        ax0, ax1, ay = (46 + bw + 18) * S, (46 + bw + 102) * S, (yb + bh / 2) * S
        d.line([(ax0, ay), (ax1 - 18 * S, ay)], fill=accent, width=8 * S)
        d.polygon([(ax1, ay), (ax1 - 30 * S, ay - 22 * S), (ax1 - 30 * S, ay + 22 * S)], fill=accent)
        y = yb + bh + 40
    if big_status:
        d.rounded_rectangle([46 * S, y * S, 466 * S, (y + 64) * S], radius=10 * S, fill=accent)
        _center_text(d, 256 * S, (y + 32) * S, big_status, font(34, mono=True), (10, 14, 22))
        y += 96

    d.text((46 * S, y * S), "FENÊTRE PRÉVUE", font=font(20, mono=True), fill=accent)
    if window:
        loc_tz = window.start.tzinfo
        rows = [(f"HEURE LOCALE ({window.start:%Z}) :", fmt_window(window, loc_tz)),
                ("HEURE DE PARIS :", fmt_window(window, TZ_PARIS))]
    else:
        rows = [("HORAIRES :", "voir le site officiel")]
    f = font(30, mono=True)
    lw = max(d.textlength(a, font=f) for a, _ in rows)
    for i, (a, b) in enumerate(rows):
        yy = (y + 36 + i * 46) * S
        d.text((46 * S, yy), a, font=f, fill=accent)
        d.text((46 * S + lw + 16 * S, yy), b, font=font(30, mono=True, bold=False), fill=(215, 220, 228))

    d.text((46 * S, 658 * S), FOOTER, font=font(20, mono=True, bold=False), fill=(120, 130, 145))

    L = 190 * S
    disc = Image.new("RGBA", (L + 20 * S, L + 20 * S), (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse([0, 0, L + 20 * S - 1, L + 20 * S - 1], fill=(255, 255, 255, 255))
    img.paste(disc, ((1280 - 50) * S - L - 10 * S, (720 - 40) * S - L - 10 * S), disc)
    lg = logo().resize((L, L), Image.LANCZOS)
    img.paste(lg, ((1280 - 50) * S - L, (720 - 40) * S - L), lg)

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.resize((1280, 720), Image.LANCZOS).save(path, optimize=True)


def road_image(path, road, chip):
    render(path, accent=AMBER, title="FERMETURE DE ROUTE",
           subtitle="VILLE DE STARBASE, TX — ACCÈS ROUTE & PLAGE",
           headline="TEXAS STATE HIGHWAY 4", headline_sub="Boca Chica Blvd · Starbase, Texas",
           boxes=(road.origin, road.destination), chip=chip, window=road.window)


def beach_image(path, window, chip):
    render(path, accent=CYAN, title="FERMETURE DE PLAGE",
           subtitle="VILLE DE STARBASE, TX — ACCÈS ROUTE & PLAGE",
           headline="BOCA CHICA BEACH", headline_sub="Plage de Starbase · Texas",
           big_status="PLAGE FERMÉE", chip=chip, window=window)

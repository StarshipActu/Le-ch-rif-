"""Lecture et analyse de https://www.starbase.texas.gov/beach-road-access"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

URL = "https://www.starbase.texas.gov/beach-road-access"
TZ_LOCAL = ZoneInfo("America/Chicago")  # heure de Starbase (CST / CDT)

# Noms des sites sur la page -> nom français
SITES_FR = {
    "pad": "SITE DE LANCEMENT",
    "launch": "SITE DE LANCEMENT",
    "launch site": "SITE DE LANCEMENT",
    "orbital launch site": "SITE DE LANCEMENT",
    "production": "SITE DE PRODUCTION",
    "production site": "SITE DE PRODUCTION",
    "massey": "SITE DE MASSEY",
    "masseys": "SITE DE MASSEY",
    "massey's": "SITE DE MASSEY",
    "massey site": "SITE DE MASSEY",
}


@dataclass
class Window:
    start: datetime  # timezone-aware, heure locale (America/Chicago)
    end: datetime


@dataclass
class RoadDelay:
    origin: str       # ex. "SITE DE LANCEMENT"
    destination: str  # ex. "SITE DE PRODUCTION"
    raw: str
    window: Window


@dataclass
class BeachInfo:
    closed_now: bool
    status_text: str
    windows: list = field(default_factory=list)


def fetch_html(url: str = URL) -> str:
    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (StarshipActu-bot; +https://github.com)"},
        timeout=30,
    )
    r.raise_for_status()
    return r.text


def _lines(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    out = []
    for raw in soup.get_text("\n").splitlines():
        s = re.sub(r"\s+", " ", raw).strip()
        if s:
            out.append(s)
    return out


def _section(lines, start_pat, end_pat=None):
    """Lignes comprises entre deux titres (insensible à la casse)."""
    s = None
    for i, l in enumerate(lines):
        if s is None and re.search(start_pat, l, re.I):
            s = i + 1
        elif s is not None and end_pat and re.search(end_pat, l, re.I):
            return lines[s:i]
    return lines[s:] if s is not None else []


def _to_dt(y, m, d, hh, mm, ampm) -> datetime:
    h = int(hh) % 12 + (12 if ampm.upper() == "PM" else 0)
    return datetime(int(y), int(m), int(d), h, int(mm), tzinfo=TZ_LOCAL)


def _site(name: str) -> str:
    key = re.sub(r"[^a-z' ]", "", name.lower()).strip()
    if key in SITES_FR:
        return SITES_FR[key]
    for k, v in SITES_FR.items():
        if k in key:
            return v
    return name.upper()


# ---------- Routes ----------
_DATE_RE = (
    r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:,?\s+(\d{4}))?,?\s+"
    r"(\d{1,2}):(\d{2})\s*([AP]M)"
)


def _month(name: str) -> int:
    return datetime.strptime(name[:3].title(), "%b").month


def parse_roads(lines, now: datetime) -> list:
    sec = _section(lines, r"^road updates", r"public notice|^previous orders")
    text = "\n".join(sec)
    roads = []
    for desc, date in re.findall(r"Description:\s*(.+?)\s*\n?\s*Date:\s*(.+)", text):
        m = re.search(_DATE_RE + r"\s*(?:to|-|–)\s*" + _DATE_RE, date, re.I)
        if not m:
            continue
        g = m.groups()
        y1 = int(g[2]) if g[2] else now.astimezone(TZ_LOCAL).year
        start = _to_dt(y1, _month(g[0]), g[1], g[3], g[4], g[5])
        y2 = int(g[8]) if g[8] else y1
        end = _to_dt(y2, _month(g[6]), g[7], g[9], g[10], g[11])
        if end < start:  # changement d'année (31 déc. -> 1er janv.)
            end = end.replace(year=end.year + 1)
        parts = re.split(r"\s+to\s+|\s*(?:→|->)\s*", desc.strip(), maxsplit=1, flags=re.I)
        if len(parts) != 2:
            continue
        roads.append(RoadDelay(_site(parts[0]), _site(parts[1]), desc.strip(), Window(start, end)))
    return roads


# ---------- Plage ----------
_PERIOD = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{2,4})\s+from\s+(\d{1,2}):(\d{2})\s*([AP]M)\s+to\s+"
    r"(\d{1,2}):(\d{2})\s*([AP]M)",
    re.I,
)


def _periods(line):
    out = []
    for m in _PERIOD.finditer(line):
        mo, d, y, h1, m1, a1, h2, m2, a2 = m.groups()
        y = int(y) + 2000 if int(y) < 100 else int(y)
        s = _to_dt(y, mo, d, h1, m1, a1)
        e = _to_dt(y, mo, d, h2, m2, a2)
        if e <= s:
            e += timedelta(days=1)
        out.append((s, e))
    return out


def parse_beach(lines, now: datetime) -> BeachInfo:
    # Statut affiché
    status = ""
    sec = _section(lines, r"beach access status", r"road updates")
    if sec:
        status = sec[0]
    closed_now = bool(re.search(r"\bclosed\b", status, re.I))

    # Arrêtés du maire
    sec = _section(lines, r"public notice of mayor", r"^previous orders")
    mode, order = None, None
    primary, revoked = [], set()
    for l in sec:
        if re.match(r"^order no\.? [\d-]+$", l, re.I):
            order, mode = l, None
        elif re.search(r"primary closure period", l, re.I):
            mode = "primary"
        elif re.search(r"alternate dates", l, re.I):
            mode = "alternate"
        elif re.search(r"revocation of closure", l, re.I):
            mode = "revoked"
        else:
            for p in _periods(l):
                if mode in ("primary", "alternate"):
                    primary.append(p)
                elif mode == "revoked":
                    revoked.add(p)
    wins = sorted({p for p in primary if p not in revoked})
    windows = [Window(s, e) for s, e in wins if e > now]
    return BeachInfo(closed_now, status, windows)


def scrape(html: str = None, now: datetime = None):
    html = html if html is not None else fetch_html()
    now = now or datetime.now(TZ_LOCAL)
    lines = _lines(html)
    roads = [r for r in parse_roads(lines, now) if r.window.end > now]
    beach = parse_beach(lines, now)
    return roads, beach

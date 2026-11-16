"""Récupère la page de Starbase et génère les visuels en français.

Usage :
    python main.py                       # données en direct
    python main.py --html page.html      # test hors-ligne
    python main.py --now 2026-11-15T12:00  # simuler une date (heure de Starbase)
Variable d'environnement optionnelle : DISCORD_WEBHOOK_URL
"""
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests

from render import beach_image, road_image
from scraper import TZ_LOCAL, scrape

OUT = Path(__file__).parent / "output"
STATE = OUT / "state.json"


def slug(s):
    return re.sub(r"[^a-z]+", "-", s.lower().replace("site de ", "")).strip("-")


def chip_for(win, now):
    return "EN COURS" if win.start <= now < win.end else "À VENIR"


def post_discord(url, path, text):
    with open(path, "rb") as f:
        r = requests.post(url, data={"content": text}, files={"file": (Path(path).name, f, "image/png")}, timeout=30)
    r.raise_for_status()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="fichier HTML local (test)")
    ap.add_argument("--now", help="date simulée AAAA-MM-JJTHH:MM (heure de Starbase)")
    a = ap.parse_args()

    now = datetime.fromisoformat(a.now).replace(tzinfo=TZ_LOCAL) if a.now else datetime.now(TZ_LOCAL)
    html = Path(a.html).read_text(encoding="utf-8") if a.html else None
    roads, beach = scrape(html, now)

    OUT.mkdir(exist_ok=True)
    items = []  # (fichier, texte discord)
    for r in roads:
        name = f"route_{slug(r.origin)}_vers_{slug(r.destination)}_{r.window.start:%Y%m%d-%H%M}.png"
        chip = chip_for(r.window, now)
        road_image(OUT / name, r, chip)
        items.append((name, chip, f"🚧 **Fermeture de route** ({chip.lower()}) : {r.origin.title()} → {r.destination.title()}"))
    for w in beach.windows:
        name = f"plage_{w.start:%Y%m%d-%H%M}.png"
        chip = chip_for(w, now)
        beach_image(OUT / name, w, chip)
        items.append((name, chip, f"🏖️ **Fermeture de plage** ({chip.lower()}) : Boca Chica Beach"))
    if beach.closed_now and not beach.windows:
        beach_image(OUT / "plage_fermee.png", None, "EN COURS")
        items.append(("plage_fermee.png", "EN COURS", "🏖️ **Plage de Boca Chica fermée**"))

    keep = {n for n, _, _ in items}
    for p in OUT.glob("*.png"):  # supprime les visuels périmés
        if p.name not in keep:
            p.unlink()

    state = json.loads(STATE.read_text()) if STATE.exists() else {"posted": []}
    hook = os.environ.get("DISCORD_WEBHOOK_URL")
    for name, chip, text in items:
        key = f"{name}|{chip}"
        if hook and key not in state["posted"]:
            post_discord(hook, OUT / name, text)
            state["posted"].append(key)
    state["posted"] = [k for k in state["posted"] if k.split("|")[0] in keep]
    STATE.write_text(json.dumps(state, indent=2))

    (OUT / "latest.json").write_text(json.dumps({
        "updated": now.isoformat(),
        "beach_status": beach.status_text,
        "files": [n for n, _, _ in items],
    }, indent=2, ensure_ascii=False))
    print(f"{len(items)} visuel(s) généré(s) :", ", ".join(keep) or "aucune fermeture active")


if __name__ == "__main__":
    main()

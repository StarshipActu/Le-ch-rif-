# Starbase Alertes 🚀

Lit en continu https://www.starbase.texas.gov/beach-road-access et génère des visuels en français
(fermetures de routes dans les deux sens + fermetures de plage) avec **heure locale (CT)** et **heure de Paris**.

## Mise en route
1. Créez un dépôt GitHub et envoyez-y tout ce dossier.
2. Onglet **Settings → Actions → General → Workflow permissions** : choisissez *Read and write permissions*.
3. Onglet **Actions** : activez les workflows, puis lancez « Mise à jour des visuels Starbase » (*Run workflow*).
4. Les images apparaissent dans `output/` et sont mises à jour automatiquement toutes les ~5 minutes.

## Discord (optionnel)
Ajoutez le secret `DISCORD_WEBHOOK_URL` (Settings → Secrets and variables → Actions) :
chaque nouvelle fermeture, ou chaque passage « À VENIR » → « EN COURS », est postée une seule fois.

## Utilisation locale
```bash
pip install -r requirements.txt
python main.py                                         # données en direct
python main.py --html tests/sample.html --now 2026-11-15T12:00   # test hors-ligne
```

## Fonctionnement
- Routes : bloc « Road Updates » (`Description: Pad to Production` → Site de lancement → Site de production).
  Noms reconnus : Pad/Launch → lancement, Production, Massey (voir `SITES_FR` dans `scraper.py`).
- Plage : « Primary Closure Period » / « Alternate Dates » des arrêtés du maire, moins les « Revocation of Closure ».
- Seules les fenêtres non terminées sont affichées ; les visuels périmés sont supprimés.
- Heure de Paris calculée automatiquement (gère les changements d'heure US/Europe).
- Logo : remplacez `assets/logo.webp` (ou ajoutez `assets/logo.png`).

⚠️ Le script dépend de la mise en page du site : si la ville la modifie, ajustez `scraper.py`.
Les cron GitHub peuvent être retardés de quelques minutes et sont suspendus après 60 jours sans activité sur le dépôt.

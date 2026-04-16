# Riftbreaker Protocol

Riftbreaker Protocol is a browser-ready 2D Pygame action RPG about storming an evil stronghold, fighting across platform-heavy stages, and chasing a princess through enemy territory.

## Highlights

- Side-view platform combat with guns and melee weapons
- Boss fights at major chapter checkpoints
- Enemy dialogue, pickups, inventory items, and power-up drops
- Save and load support from the title screen
- Pause menu, HUD, and browser-ready async game loop
- Procedural world music and weather-driven atmosphere

## Local Run

```bash
pip install -r requirements.txt
python main.py
```

## Browser Build

```bash
python -m pygbag --build --html .
python scripts/prepare_pages.py
```

That produces a GitHub Pages-ready `dist/` folder with:

- `index.html`
- `404.html`
- the packaged game archive from `pygbag`

## GitHub Pages Deploy

This repo includes a GitHub Pages workflow in `.github/workflows/deploy-pages.yml`.

To publish it:

1. Push to `main` or `master`.
2. In GitHub, open `Settings` -> `Pages`.
3. Set the source to `GitHub Actions`.
4. Wait for the `Deploy GitHub Pages` workflow to finish.

GitHub will then give you a public Pages URL anyone can open in a browser.

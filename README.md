# Riftbreaker Protocol

Riftbreaker Protocol is a browser-ready Pygame platform action RPG about storming an evil empire, climbing from the outer perimeter into the Eclipse Sea wreck fleet, and hunting for a trapped princess.

## Game Structure

- 5 worlds
- 25 levels total
- Boss fights on levels 5, 10, 15, 20, and 25
- After every 5 levels, the next route opens through a world selection screen
- Platforming, jumping, ranged combat, and melee weapons
- Weapon pickups hidden around levels
- Inventory items like medkits and story loot
- Spinning Wheel pickups can award extra lives up to a 5-life cap
- HP grows as you earn XP, with bigger boosts on full level-ups
- Armor Suit drops add a breakable armor bar that can be repaired by more armor pickups
- Random enemy power-up drops like Shield, Gun Boost, and Speed Boost
- World 4 adds snow hazards with enemy-thrown bombs and falling ice spikes
- World 5 adds the Eclipse Sea, tougher wreck-fleet enemies, and Captain Rook support fire plus on-call healing
- Enemy speech bubbles and story dialogue panels
- Save and load support from the title screen
- A Tab pause menu with resume, save, and quit-to-title options
- A new Abyss Warden chapter ending with a "to be continued" screen

## Story

Princess Elara has been captured deep inside the Blackfang empire. You play as the breaker sent to cut through the outer ruins, break into the base, climb the Crown Spire, breach Frostfall Bastion, cross the Eclipse Sea with Captain Rook, defeat its bosses, and track her location through the first chapter of the rescue.

## Controls

- `A` / `D`: move
- `W` or `Up`: jump
- `Space`: attack with the equipped weapon
- `Q` / `E`: cycle weapons
- `1`: use a medkit to heal
- Spinning Wheels: auto-spin on pickup and can raise lives up to 5
- `H`: call Captain Rook for a heal in World 5 when his support cooldown is ready
- `I`: toggle inventory
- `Tab`: open the pause menu
- `Enter`: advance dialogue or continue to the next level after clearing a stage
- `Esc`: quit

## Local Run

```bash
pip install -r requirements.txt
python main.py
```

## Browser Build

This project uses an async `main.py` entry loop so it can be packaged for the web with `pygbag`.

From the project root, run:

```bash
python -m pygbag --build --html .
python scripts/prepare_pages.py
```

That produces a GitHub Pages-ready `dist/` folder with:

- `index.html`
- `404.html`
- the packaged game archive from `pygbag`

## GitHub Pages Deploy

This repo now includes a GitHub Pages workflow in `.github/workflows/deploy-pages.yml`.

To publish it:

1. Put the `shooter_rpg_web` folder in a GitHub repository.
2. Push to the `main` branch or `master` branch.
3. In GitHub, open `Settings` -> `Pages`.
4. Set the source to `GitHub Actions`.
5. Push again if needed, then wait for the `Deploy GitHub Pages` workflow to finish.

GitHub will then give you a public Pages URL that anyone can open in a browser to play.

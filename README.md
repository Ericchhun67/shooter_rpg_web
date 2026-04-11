# Riftbreaker Protocol

Riftbreaker Protocol is a browser-ready Pygame platform action RPG about storming an evil base and hunting for a trapped princess.

## Game Structure

- 2 worlds
- 10 levels total
- Boss fights on levels 5 and 10
- After every 5 levels, the next route opens through a world selection screen
- Platforming, jumping, ranged combat, and melee weapons
- Weapon pickups hidden around levels
- Inventory items like medkits and story loot
- Random enemy power-up drops like Shield, Gun Boost, and Speed Boost
- Enemy speech bubbles and story dialogue panels
- Save and load support from the title screen
- A Tab pause menu with resume, save, and quit-to-title options
- A cliffhanger chapter ending with a "to be continued" screen

## Story

Princess Elara has been captured deep inside the Blackfang Base. You play as the breaker sent to cut through the outer ruins, enter the base, defeat its bosses, and track her location through the first chapter of the rescue.

## Controls

- `A` / `D`: move
- `W` or `Up`: jump
- `Space`: attack with the equipped weapon
- `Q` / `E`: cycle weapons
- `1`: use a medkit to heal
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

From the parent directory, run:

```bash
python -m pygbag shooter_rpg_web
```

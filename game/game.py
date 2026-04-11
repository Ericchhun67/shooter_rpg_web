from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from game.audio import MusicManager
from game import settings
from game.entities import Bullet, Enemy, FloatingText, Pickup, Player
from game.save_system import load_save_data, save_exists, write_save_data

Vec2 = pygame.Vector2 # Simple alias for 2D Vector type from pygame


@dataclass # Using dataclass for simple storage of dialogue sequence
class DialogueSequence:
    """ 
    Represents a sequence of dialogue lines from a speaker, with an associated accent color. 
    The index tracks the current line being displayed in the sequence.
    
    """
    speaker: str # Name of the character speaking the dialogue
    lines: list[str] # List of dialogue lines to be displayed in sequence
    accent: tuple[int, int, int] # RGB color for the speaker's name or dialogue accent
    index: int = 0 # Current index in the lines list, defaults to 0

    @property # Property to get the current line of dialogue based on the index
    def current_line(self) -> str:
        # Returns the current line of dialogue, or an empty string if the index is out of bounds
        return self.lines[self.index]

# Utility function to wrap text into multiple lines based on a given width and font metrices.
def wrap_text(font: pygame.font.Font, text: str, width: int) -> list[str]:
    words = text.split() # Split the input text into individual words
    lines: list[str] = [] # empty list to hold the resulting lines of wrapped text
    current = "" # current line being built to an empty string
    # loop through each words and build lines that fit within the specified width
    for word in words:
        # Check if adding the next word would exceed the width when rendered with the font
        candidate = f"{current} {word}".strip()
        # if the candidate line fits within the width, update the current line, 
        # otherwise, add the current line to the lines list and start a new line with
        # the current word
        if font.size(candidate)[0] <= width:
            # let the candidate line become the current line if it fits within the width
            current = candidate
        else: # else, the candidate line exceeds the width, so we add the current
            # line to the lines list and start a new line with the current word
            if current:# then add the current line to the lines list if it's not
                # empty
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    # return the list of lines that have been wrapped according to the specified width
    # and font
    return lines

# Utility function to linearly interpolate between two RGB colors based on a 
# parameter that ranges from 0 to 1, where 0 returns the start color and 1 returns an end color.
def lerp_color(start: tuple[int, int, int], end: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(start[index] + (end[index] - start[index]) * t) for index in range(3))


class RiftbreakerGame:
    """ 
    Main game class that encapsulates the game state, including player,
    enemies, pickups, and game logic for handling events, updating the game state,
    and rendering the game. It also manages the game flow, such as loading levels,
    handling dialogue sequences, and saving/loading game state.
    
    
    """
    def __init__(self) -> None:
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption(settings.TITLE)
        self.screen = pygame.display.set_mode((settings.WIDTH, settings.HEIGHT))
        self.clock = pygame.time.Clock()
        self.fps = settings.FPS
        self.running = True

        self.font_title = pygame.font.SysFont("georgia", 48, bold=True)
        self.font_large = pygame.font.SysFont("consolas", 28, bold=True)
        self.font_medium = pygame.font.SysFont("consolas", 22)
        self.font_small = pygame.font.SysFont("consolas", 18)

        self.state = "menu"
        self.inventory_open = False
        self.pause_menu_open = False
        self.story_dialogue: DialogueSequence | None = None
        self.level_index = 0
        self.level_complete = False
        self.ending_ready = False
        self.run_seed = random.randint(1000, 9999)
        self.slash_effect: dict | None = None
        self.lightning_timer = 0.0
        self.next_lightning = random.uniform(2.8, 5.3)
        self.music = MusicManager()
        self.menu_index = 0
        self.pause_index = 0
        self.world_select_index = 0
        self.menu_message = ""
        self.pause_message = ""
        self.max_world_unlocked = 1

        self.player = Player(80, 590)
        self.platforms: list[pygame.Rect] = [pygame.Rect(*platform) for platform in settings.LEVELS[0]["platforms"]]
        self.enemies: list[Enemy] = []
        self.pickups: list[Pickup] = []
        self.player_bullets: list[Bullet] = []
        self.enemy_bullets: list[Bullet] = []
        self.floating_texts: list[FloatingText] = []

    @property
    def level_data(self) -> dict:
        return settings.LEVELS[self.level_index]

    @property
    def theme(self) -> dict:
        return settings.WORLD_THEMES[self.level_data["world"]]

    def reset_run(self) -> None:
        self.state = "playing"
        self.inventory_open = False
        self.pause_menu_open = False
        self.story_dialogue = None
        self.level_complete = False
        self.ending_ready = False
        self.run_seed = random.randint(1000, 9999)
        self.slash_effect = None
        self.lightning_timer = 0.0
        self.next_lightning = random.uniform(2.8, 5.3)
        self.menu_message = ""
        self.pause_message = ""
        self.max_world_unlocked = 1
        self.world_select_index = 0

        self.player = Player(*settings.LEVELS[0]["spawn"])
        self.player.items["medkit"] = 2
        self.player_bullets.clear()
        self.enemy_bullets.clear()
        self.pickups.clear()
        self.floating_texts.clear()
        self.load_level(0)

    def open_dialogue(self, speaker: str, lines: list[str], accent: tuple[int, int, int]) -> None:
        self.story_dialogue = DialogueSequence(speaker, lines, accent)

    def advance_dialogue(self) -> None:
        if not self.story_dialogue:
            return
        self.story_dialogue.index += 1
        if self.story_dialogue.index >= len(self.story_dialogue.lines):
            self.story_dialogue = None

    def spawn_pickup(self, pickup_type: str, pickup_id: str, x: int, y: int) -> None:
        if pickup_type == "weapon":
            weapon = settings.WEAPON_DATA[pickup_id]
            label = weapon["name"]
            color = weapon["color"]
        elif pickup_type == "powerup":
            powerup = settings.POWERUP_DATA[pickup_id]
            label = powerup["name"]
            color = powerup["color"]
        else:
            item = settings.ITEM_DATA[pickup_id]
            label = item["name"]
            color = item["color"]
        self.pickups.append(Pickup(pickup_type, pickup_id, pygame.Rect(x, y, 34, 34), color, label))

    def load_level(self, index: int) -> None:
        self.level_index = index
        data = self.level_data
        self.max_world_unlocked = max(self.max_world_unlocked, data["world"])
        self.platforms = [pygame.Rect(*platform) for platform in data["platforms"]]
        self.enemies = [
            Enemy(spawn["kind"], spawn["x"], spawn["y"], spawn["line"], spawn.get("patrol"), spawn.get("name"))
            for spawn in data["enemy_spawns"]
        ]
        self.pickups = []
        for pickup in data["weapon_pickups"]:
            self.spawn_pickup("weapon", pickup["weapon_id"], pickup["x"], pickup["y"])
        for pickup in data["item_pickups"]:
            self.spawn_pickup("item", pickup["item_id"], pickup["x"], pickup["y"])

        spawn_x, spawn_y = data["spawn"]
        self.player.set_spawn(spawn_x, spawn_y)
        self.player.hp = min(self.player.max_hp, self.player.hp + 12)
        self.player_bullets.clear()
        self.enemy_bullets.clear()
        self.level_complete = False
        self.ending_ready = False
        self.slash_effect = None
        self.floating_texts.append(
            FloatingText(f"Level {data['level']}: {data['name']}", Vec2(settings.WIDTH / 2, 82), settings.GOLD, 1.9)
        )
        self.open_dialogue("Archivist Nia", data["intro"], settings.ACCENT)
        self.sync_music()

    def next_level(self) -> None:
        if self.level_index + 1 < len(settings.LEVELS):
            self.load_level(self.level_index + 1)

    def sync_music(self) -> None:
        if self.state != "playing":
            self.music.stop()
            return

        if self.level_data["world"] == 1:
            self.music.play("storm_siege_road")
        elif self.level_data["world"] == 2:
            self.music.play("blackfang_core")
        else:
            self.music.stop()

    def menu_options(self) -> list[str]:
        return ["New Game", "Load Game", "Quit"]

    def pause_options(self) -> list[str]:
        return ["Resume", "Save Game", "Quit to Main Menu"]

    def world_ids(self) -> list[int]:
        return sorted({level["world"] for level in settings.LEVELS})

    def selectable_worlds(self) -> list[int]:
        return [world_id for world_id in self.world_ids() if world_id <= self.max_world_unlocked]

    def first_level_index_for_world(self, world_id: int) -> int:
        for index, level in enumerate(settings.LEVELS):
            if level["world"] == world_id:
                return index
        return 0

    def level_range_for_world(self, world_id: int) -> tuple[int, int]:
        levels = [level["level"] for level in settings.LEVELS if level["world"] == world_id]
        return (levels[0], levels[-1])

    def open_world_selection(self, preferred_world: int | None = None) -> None:
        worlds = self.selectable_worlds()
        if not worlds:
            return
        self.music.stop()
        self.state = "world_select"
        self.inventory_open = False
        self.pause_menu_open = False
        self.story_dialogue = None
        target_world = preferred_world if preferred_world in worlds else worlds[-1]
        self.world_select_index = worlds.index(target_world)
        self.menu_message = ""
        self.pause_message = ""

    def open_main_menu(self, message: str = "") -> None:
        self.music.stop()
        self.state = "menu"
        self.level_index = 0
        self.inventory_open = False
        self.pause_menu_open = False
        self.story_dialogue = None
        self.level_complete = False
        self.ending_ready = False
        self.slash_effect = None
        self.platforms = [pygame.Rect(*platform) for platform in settings.LEVELS[0]["platforms"]]
        self.enemies = []
        self.pickups = []
        self.player_bullets.clear()
        self.enemy_bullets.clear()
        self.floating_texts.clear()
        self.lightning_timer = 0.0
        self.next_lightning = random.uniform(2.8, 5.3)
        self.menu_index = 0
        self.pause_index = 0
        self.world_select_index = 0
        self.menu_message = message
        self.pause_message = ""

    def build_save_data(self) -> dict:
        dialogue = None
        if self.story_dialogue:
            dialogue = {
                "speaker": self.story_dialogue.speaker,
                "lines": list(self.story_dialogue.lines),
                "accent": list(self.story_dialogue.accent),
                "index": self.story_dialogue.index,
            }

        return {
            "level_index": self.level_index,
            "run_seed": self.run_seed,
            "level_complete": self.level_complete,
            "ending_ready": self.ending_ready,
            "lightning_timer": self.lightning_timer,
            "next_lightning": self.next_lightning,
            "max_world_unlocked": self.max_world_unlocked,
            "player": self.player.to_save_data(),
            "enemies": [enemy.to_save_data() for enemy in self.enemies],
            "pickups": [pickup.to_save_data() for pickup in self.pickups],
            "story_dialogue": dialogue,
        }

    def restore_from_save(self, data: dict) -> None:
        level_index = max(0, min(int(data["level_index"]), len(settings.LEVELS) - 1))
        self.state = "playing"
        self.inventory_open = False
        self.pause_menu_open = False
        self.menu_message = ""
        self.pause_message = ""
        self.run_seed = int(data.get("run_seed", self.run_seed))
        self.max_world_unlocked = int(data.get("max_world_unlocked", self.max_world_unlocked))
        self.load_level(level_index)

        self.player.apply_save_data(data["player"])
        self.enemies = [Enemy.from_save_data(entry) for entry in data.get("enemies", [])]
        self.pickups = [Pickup.from_save_data(entry) for entry in data.get("pickups", [])]
        self.player_bullets.clear()
        self.enemy_bullets.clear()
        self.floating_texts.clear()
        self.slash_effect = None
        self.level_complete = bool(data.get("level_complete", False))
        self.ending_ready = bool(data.get("ending_ready", False))
        self.lightning_timer = max(0.0, float(data.get("lightning_timer", 0.0)))
        self.next_lightning = max(0.1, float(data.get("next_lightning", random.uniform(2.8, 5.3))))

        dialogue = data.get("story_dialogue")
        if dialogue:
            self.story_dialogue = DialogueSequence(
                dialogue["speaker"],
                list(dialogue["lines"]),
                tuple(dialogue["accent"]),
                int(dialogue.get("index", 0)),
            )
        else:
            self.story_dialogue = None

        self.sync_music()

    def save_game(self) -> tuple[bool, str]:
        if self.state != "playing":
            return False, "You can only save during a run."

        try:
            write_save_data(self.build_save_data())
        except (OSError, TypeError, ValueError):
            return False, "Save failed. Try again."
        return True, "Game saved."

    def load_game(self) -> tuple[bool, str]:
        try:
            data = load_save_data()
        except (OSError, ValueError):
            return False, "Save file could not be loaded."

        if not data:
            return False, "No save game found."

        try:
            self.restore_from_save(data)
        except (KeyError, TypeError, ValueError):
            return False, "Save file is corrupted."
        return True, "Game loaded."

    def drop_enemy_loot(self, enemy: Enemy) -> None:
        levels = self.player.gain_xp(enemy.xp_reward)
        self.floating_texts.append(FloatingText(f"+{enemy.xp_reward} XP", Vec2(enemy.rect.center), settings.ACCENT, 1.2))
        if levels:
            self.floating_texts.append(
                FloatingText(f"Level {self.player.level}", Vec2(enemy.rect.centerx, enemy.rect.top - 28), settings.GOLD, 1.6)
            )

        drop_pool = ["alloy_scrap", "medkit"]
        weights = [3, 1]
        if enemy.is_boss:
            boss_drop = "warden_core"
            self.player.add_item(boss_drop, 1)
            self.floating_texts.append(FloatingText(settings.ITEM_DATA[boss_drop]["name"], Vec2(enemy.rect.centerx, enemy.rect.top - 24), settings.WARN, 1.5))
        elif random.random() < 0.3:
            item_id = random.choices(drop_pool, weights=weights, k=1)[0]
            self.spawn_pickup("item", item_id, enemy.rect.centerx - 17, enemy.rect.centery - 17)

        powerup_chance = settings.BOSS_POWERUP_DROP_CHANCE if enemy.is_boss else settings.POWERUP_DROP_CHANCE
        if random.random() < powerup_chance:
            powerup_id = random.choices(settings.POWERUP_DROP_POOL, weights=settings.POWERUP_DROP_WEIGHTS, k=1)[0]
            self.spawn_pickup("powerup", powerup_id, enemy.rect.centerx - 17, enemy.rect.centery - 52)

    def maybe_complete_level(self) -> None:
        if self.level_complete or self.enemies:
            return

        self.level_complete = True
        level_number = self.level_data["level"]
        if level_number == 10:
            self.ending_ready = True
            self.open_dialogue(
                "Archivist Nia",
                [
                    "Malgrin is down, but the cell is empty. The princess was transferred before you arrived.",
                    "Blackfang logs point to a higher fortress beyond this base. Press Enter and we'll follow the trail.",
                ],
                settings.GOLD,
            )
            return

        if level_number == 5:
            next_world = self.level_data["world"] + 1
            if next_world in self.world_ids():
                self.max_world_unlocked = max(self.max_world_unlocked, next_world)
            self.open_dialogue(
                "Archivist Nia",
                [
                    "The first boss is down. The Blackfang Base entrance is open.",
                    "Press Enter to open the world selection and choose your next route.",
                ],
                settings.SUCCESS,
            )
        else:
            self.floating_texts.append(
                FloatingText("Level clear. Press Enter to continue.", Vec2(settings.WIDTH / 2, 116), settings.SUCCESS, 2.5)
            )

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
                return

            if self.state == "menu":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_w, pygame.K_UP):
                        self.menu_index = (self.menu_index - 1) % len(self.menu_options())
                        self.menu_message = ""
                    elif event.key in (pygame.K_s, pygame.K_DOWN):
                        self.menu_index = (self.menu_index + 1) % len(self.menu_options())
                        self.menu_message = ""
                    elif event.key == pygame.K_RETURN:
                        selection = self.menu_options()[self.menu_index]
                        if selection == "New Game":
                            self.reset_run()
                        elif selection == "Load Game":
                            loaded, message = self.load_game()
                            if not loaded:
                                self.menu_message = message
                        else:
                            self.running = False
                continue

            if self.state == "world_select":
                worlds = self.selectable_worlds()
                if event.type == pygame.KEYDOWN and worlds:
                    if event.key in (pygame.K_a, pygame.K_LEFT):
                        self.world_select_index = (self.world_select_index - 1) % len(worlds)
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        self.world_select_index = (self.world_select_index + 1) % len(worlds)
                    elif event.key == pygame.K_RETURN:
                        selected_world = worlds[self.world_select_index]
                        self.state = "playing"
                        self.load_level(self.first_level_index_for_world(selected_world))
                continue

            if self.state in {"gameover", "tbc"}:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    self.open_main_menu()
                continue

            if event.type == pygame.KEYDOWN:
                if self.pause_menu_open:
                    if event.key == pygame.K_TAB:
                        self.pause_menu_open = False
                        self.pause_message = ""
                    elif event.key in (pygame.K_w, pygame.K_UP):
                        self.pause_index = (self.pause_index - 1) % len(self.pause_options())
                        self.pause_message = ""
                    elif event.key in (pygame.K_s, pygame.K_DOWN):
                        self.pause_index = (self.pause_index + 1) % len(self.pause_options())
                        self.pause_message = ""
                    elif event.key == pygame.K_RETURN:
                        selection = self.pause_options()[self.pause_index]
                        if selection == "Resume":
                            self.pause_menu_open = False
                            self.pause_message = ""
                        elif selection == "Save Game":
                            _, self.pause_message = self.save_game()
                        else:
                            self.open_main_menu("Run paused at the title screen.")
                    continue

                if event.key == pygame.K_TAB:
                    self.pause_menu_open = True
                    self.pause_index = 0
                    self.pause_message = ""
                    self.inventory_open = False
                elif event.key in (pygame.K_w, pygame.K_UP) and not self.story_dialogue:
                    self.player.jump()
                elif event.key == pygame.K_i:
                    self.inventory_open = not self.inventory_open
                elif event.key == pygame.K_q:
                    self.player.cycle_weapon(-1)
                elif event.key == pygame.K_e:
                    self.player.cycle_weapon(1)
                elif event.key == pygame.K_1:
                    if self.player.use_medkit():
                        self.floating_texts.append(FloatingText("Medkit used", Vec2(self.player.rect.center), settings.SUCCESS, 1.0))
                elif event.key == pygame.K_RETURN:
                    if self.story_dialogue:
                        self.advance_dialogue()
                    elif self.ending_ready:
                        self.state = "tbc"
                    elif self.level_complete:
                        if self.level_data["level"] % 5 == 0:
                            next_world = self.level_data["world"] + 1
                            if next_world in self.world_ids():
                                self.max_world_unlocked = max(self.max_world_unlocked, next_world)
                                self.open_world_selection(next_world)
                            else:
                                self.next_level()
                        else:
                            self.next_level()

    def update_floating_texts(self, dt: float) -> None:
        active: list[FloatingText] = []
        for text in self.floating_texts:
            if text.update(dt):
                active.append(text)
        self.floating_texts = active

    def update_world_backgrounds(self, dt: float) -> None:
        self.lightning_timer = max(0.0, self.lightning_timer - dt)
        self.next_lightning -= dt
        if self.level_data["world"] == 1 and self.next_lightning <= 0.0:
            self.lightning_timer = random.uniform(0.10, 0.22)
            self.next_lightning = random.uniform(2.6, 5.8)

    def update(self, dt: float) -> None:
        if self.state != "playing":
            self.update_world_backgrounds(dt)
            return

        if self.pause_menu_open:
            return

        self.update_floating_texts(dt)
        self.update_world_backgrounds(dt)
        if self.slash_effect:
            self.slash_effect["timer"] -= dt
            if self.slash_effect["timer"] <= 0:
                self.slash_effect = None

        for pickup in self.pickups:
            pickup.update(dt)

        if self.story_dialogue:
            return

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        self.player.update(dt, keys, self.platforms, mouse_pos)

        attack_pressed = keys[pygame.K_SPACE]
        if attack_pressed:
            bullets, slash_rect, slash_damage, slash_color = self.player.attack(mouse_pos)
            if bullets:
                self.player_bullets.extend(bullets)
            if slash_rect:
                self.slash_effect = {"rect": slash_rect.copy(), "timer": 0.12, "color": slash_color}
                for enemy in self.enemies:
                    if enemy.rect.colliderect(slash_rect):
                        enemy.hit(slash_damage)
                        self.floating_texts.append(
                            FloatingText(f"-{int(slash_damage)}", Vec2(enemy.rect.centerx, enemy.rect.top - 10), settings.WARN, 0.7)
                        )

        self.player_bullets = [bullet for bullet in self.player_bullets if bullet.update(dt, self.platforms)]
        self.enemy_bullets = [bullet for bullet in self.enemy_bullets if bullet.update(dt, self.platforms)]

        new_enemy_bullets: list[Bullet] = []
        for enemy in self.enemies:
            new_enemy_bullets.extend(enemy.update(dt, self.player, self.platforms))
        self.enemy_bullets.extend(new_enemy_bullets)

        remaining_player_bullets: list[Bullet] = []
        for bullet in self.player_bullets:
            hit = False
            for enemy in self.enemies:
                if bullet.rect.colliderect(enemy.rect):
                    if enemy.blocks_projectile(bullet):
                        enemy.flash = 0.45
                        self.floating_texts.append(FloatingText("Blocked", Vec2(enemy.rect.centerx, enemy.rect.top - 8), settings.GOLD, 0.6))
                    else:
                        enemy.hit(bullet.damage)
                        self.floating_texts.append(FloatingText(f"-{int(bullet.damage)}", Vec2(enemy.rect.center), settings.WARN, 0.65))
                    hit = True
                    break
            if not hit:
                remaining_player_bullets.append(bullet)
        self.player_bullets = remaining_player_bullets

        defeated = [enemy for enemy in self.enemies if enemy.hp <= 0]
        if defeated:
            for enemy in defeated:
                self.drop_enemy_loot(enemy)
                if enemy.kind == "thorn_warden":
                    self.player.add_item("prison_key", 1)
                if enemy.kind == "lord_malgrin":
                    self.player.add_item("royal_seal", 1)
            self.enemies = [enemy for enemy in self.enemies if enemy.hp > 0]

        remaining_enemy_bullets: list[Bullet] = []
        for bullet in self.enemy_bullets:
            if bullet.rect.colliderect(self.player.rect):
                damage_result, amount = self.player.receive_damage(bullet.damage)
                if damage_result == "hp":
                    self.floating_texts.append(FloatingText(f"-{int(amount)} HP", Vec2(self.player.rect.center), settings.WARN, 0.8))
                elif damage_result == "shield":
                    self.floating_texts.append(FloatingText("Shield", Vec2(self.player.rect.center), settings.ACCENT, 0.8))
            else:
                remaining_enemy_bullets.append(bullet)
        self.enemy_bullets = remaining_enemy_bullets

        for enemy in self.enemies:
            if enemy.rect.colliderect(self.player.rect):
                damage_result, amount = self.player.receive_damage(enemy.damage)
                if damage_result == "hp":
                    knockback = 180 if enemy.rect.centerx < self.player.rect.centerx else -180
                    self.player.vel.x = knockback
                    self.player.vel.y = -220
                    self.floating_texts.append(FloatingText(f"-{int(amount)} HP", Vec2(self.player.rect.centerx, self.player.rect.top - 10), settings.WARN, 0.8))
                elif damage_result == "shield":
                    self.floating_texts.append(FloatingText("Shield", Vec2(self.player.rect.centerx, self.player.rect.top - 10), settings.ACCENT, 0.8))

        remaining_pickups: list[Pickup] = []
        for pickup in self.pickups:
            if self.player.rect.colliderect(pickup.rect.inflate(8, 8)):
                if pickup.pickup_type == "weapon":
                    if self.player.add_weapon(pickup.pickup_id):
                        self.floating_texts.append(
                            FloatingText(settings.WEAPON_DATA[pickup.pickup_id]["name"], Vec2(pickup.rect.center), pickup.color, 1.4)
                        )
                elif pickup.pickup_type == "powerup":
                    self.player.activate_powerup(pickup.pickup_id)
                    self.floating_texts.append(
                        FloatingText(settings.POWERUP_DATA[pickup.pickup_id]["name"], Vec2(pickup.rect.center), pickup.color, 1.5)
                    )
                else:
                    self.player.add_item(pickup.pickup_id, 1)
                    self.floating_texts.append(
                        FloatingText(settings.ITEM_DATA[pickup.pickup_id]["name"], Vec2(pickup.rect.center), pickup.color, 1.2)
                    )
            else:
                remaining_pickups.append(pickup)
        self.pickups = remaining_pickups

        if self.player.hp <= 0:
            self.music.stop()
            self.state = "gameover"
            return

        self.maybe_complete_level()

    def draw_world1_background(self) -> None:
        sky_top = (22, 28, 44)
        sky_bottom = (72, 66, 78)
        flash_strength = self.lightning_timer / 0.22 if self.lightning_timer > 0 else 0.0
        ticks = pygame.time.get_ticks() / 1000.0

        for band in range(12):
            t = band / 11
            color = lerp_color(sky_top, sky_bottom, t)
            color = tuple(min(255, int(channel + 50 * flash_strength)) for channel in color)
            rect = pygame.Rect(0, band * 64, settings.WIDTH, 64)
            pygame.draw.rect(self.screen, color, rect)

        cloud_surface = pygame.Surface((settings.WIDTH, 280), pygame.SRCALPHA)
        for index in range(7):
            base_x = 80 + index * 178 + math.sin(ticks * 0.18 + index) * 18
            base_y = 66 + (index % 3) * 28
            color = (18, 22, 31, 170)
            pygame.draw.ellipse(cloud_surface, color, pygame.Rect(base_x, base_y, 220, 74))
            pygame.draw.ellipse(cloud_surface, (30, 34, 46, 120), pygame.Rect(base_x - 38, base_y + 22, 260, 62))
        self.screen.blit(cloud_surface, (0, 0))

        rain_color = (188, 205, 228)
        for index in range(28):
            x = (index * 63 + ticks * 210) % (settings.WIDTH + 120) - 60
            y = (index * 37 + ticks * 120) % 430
            pygame.draw.line(self.screen, rain_color, (x, y), (x - 18, y + 42), 1)

        mountain_back = [
            (0, 430), (120, 286), (206, 348), (326, 248), (440, 338), (560, 224),
            (690, 322), (844, 238), (936, 320), (1090, 210), (1212, 304), (1280, 252),
            (1280, 520), (0, 520),
        ]
        mountain_front = [
            (0, 476), (98, 366), (188, 422), (292, 330), (424, 446), (566, 302),
            (672, 388), (824, 294), (948, 400), (1106, 312), (1280, 420), (1280, 540), (0, 540),
        ]
        pygame.draw.polygon(self.screen, (29, 35, 43), mountain_back)
        pygame.draw.polygon(self.screen, (41, 44, 52), mountain_front)

        wall_rect = pygame.Rect(0, 410, settings.WIDTH, 86)
        pygame.draw.rect(self.screen, (47, 47, 55), wall_rect)
        for x in range(0, settings.WIDTH + 1, 54):
            battlement = pygame.Rect(x + 8, wall_rect.top - 24, 30, 24)
            pygame.draw.rect(self.screen, (58, 58, 68), battlement)

        tower_positions = [154, 418, 884, 1118]
        for index, tower_x in enumerate(tower_positions):
            tower = pygame.Rect(tower_x, 196 + (index % 2) * 28, 62, 214)
            pygame.draw.rect(self.screen, (55, 50, 60), tower, border_radius=4)
            roof = [(tower.left - 16, tower.top + 18), (tower.centerx, tower.top - 28), (tower.right + 16, tower.top + 18)]
            pygame.draw.polygon(self.screen, (78, 60, 58), roof)
            banner = pygame.Rect(tower.centerx + 16, tower.top + 38, 10, 64)
            pygame.draw.rect(self.screen, (130, 26, 26), banner, border_radius=3)
            pygame.draw.circle(self.screen, (255, 126, 86), (tower.centerx, tower.top + 88), 5)

        road = [(0, settings.HEIGHT), (settings.WIDTH, settings.HEIGHT), (884, 456), (396, 456)]
        pygame.draw.polygon(self.screen, (72, 56, 49), road)
        pygame.draw.polygon(self.screen, (104, 80, 67), [(500, settings.HEIGHT), (780, settings.HEIGHT), (692, 456), (588, 456)])
        pygame.draw.line(self.screen, (146, 116, 90), (628, settings.HEIGHT), (612, 456), 4)
        pygame.draw.line(self.screen, (146, 116, 90), (724, settings.HEIGHT), (676, 456), 4)

        for base_x in (170, 294, 948, 1084):
            for offset in (-18, 0, 18):
                pygame.draw.line(self.screen, (128, 98, 76), (base_x - 22, 612 + offset // 2), (base_x + 22, 664 + offset), 5)
                pygame.draw.line(self.screen, (128, 98, 76), (base_x + 22, 612 + offset // 2), (base_x - 22, 664 + offset), 5)

        for smoke_x, smoke_y in ((228, 420), (520, 390), (994, 404)):
            for puff in range(5):
                radius = 24 + puff * 10
                drift_x = smoke_x + math.sin(ticks * 0.5 + puff) * 14 - puff * 10
                drift_y = smoke_y - puff * 26 - math.cos(ticks * 0.42 + puff) * 6
                smoke = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(smoke, (28, 30, 36, 65), (smoke.get_width() // 2, smoke.get_height() // 2), radius)
                self.screen.blit(smoke, smoke.get_rect(center=(drift_x, drift_y)))

        if flash_strength > 0:
            flash = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
            flash.fill((220, 228, 255, int(84 * flash_strength)))
            self.screen.blit(flash, (0, 0))
            bolt_points = [
                (920, 18), (884, 110), (928, 110), (858, 236), (914, 236), (846, 372),
            ]
            pygame.draw.lines(self.screen, (244, 248, 255), False, bolt_points, 5)
            pygame.draw.lines(self.screen, (170, 210, 255), False, bolt_points, 2)

    def draw_world2_background(self) -> None:
        ticks = pygame.time.get_ticks() / 1000.0
        top = (24, 18, 23)
        mid = (57, 31, 27)
        bottom = (92, 47, 33)

        for band in range(12):
            t = band / 11
            color = lerp_color(top, mid if t < 0.55 else bottom, t if t < 0.55 else (t - 0.55) / 0.45)
            rect = pygame.Rect(0, band * 64, settings.WIDTH, 64)
            pygame.draw.rect(self.screen, color, rect)

        furnace_glow = pygame.Surface((settings.WIDTH, 260), pygame.SRCALPHA)
        for index in range(5):
            glow_rect = pygame.Rect(120 + index * 250, settings.HEIGHT - 184 + (index % 2) * 18, 220, 180)
            pygame.draw.ellipse(furnace_glow, (255, 128, 62, 42), glow_rect)
        self.screen.blit(furnace_glow, (0, 0))

        back_towers = [
            pygame.Rect(92, 126, 124, 396),
            pygame.Rect(312, 162, 148, 352),
            pygame.Rect(612, 92, 170, 432),
            pygame.Rect(928, 148, 144, 362),
            pygame.Rect(1146, 112, 132, 398),
        ]
        for tower in back_towers:
            pygame.draw.rect(self.screen, (45, 42, 48), tower, border_radius=8)
            for offset in range(0, tower.height - 60, 60):
                window = pygame.Rect(tower.x + 18, tower.y + 20 + offset, tower.width - 36, 12)
                pygame.draw.rect(self.screen, (103, 64, 48), window, border_radius=5)
            vent = pygame.Rect(tower.centerx - 14, tower.y - 26, 28, 34)
            pygame.draw.rect(self.screen, (62, 58, 66), vent, border_radius=6)

        chain_color = (69, 66, 72)
        for chain_x in (214, 524, 838, 1158):
            for link in range(14):
                rect = pygame.Rect(chain_x - 8, 44 + link * 34, 16, 26)
                pygame.draw.ellipse(self.screen, chain_color, rect, 4)

        catwalks = [
            pygame.Rect(0, 468, settings.WIDTH, 34),
            pygame.Rect(138, 320, 286, 16),
            pygame.Rect(854, 278, 262, 16),
        ]
        for catwalk in catwalks:
            pygame.draw.rect(self.screen, (73, 71, 76), catwalk)
            pygame.draw.rect(self.screen, (124, 102, 88), catwalk, 2)
            for x in range(catwalk.left + 12, catwalk.right - 12, 28):
                pygame.draw.line(self.screen, (136, 113, 95), (x, catwalk.top), (x + 16, catwalk.bottom), 1)

        pipe_sets = [
            ((0, 206), (settings.WIDTH, 206), 12),
            ((0, 246), (settings.WIDTH, 246), 8),
            ((120, 560), (1260, 560), 18),
        ]
        for start, end, width in pipe_sets:
            pygame.draw.line(self.screen, (96, 86, 82), start, end, width)
            pygame.draw.line(self.screen, (155, 126, 110), (start[0], start[1] - width // 3), (end[0], end[1] - width // 3), 2)

        prison_block = pygame.Rect(settings.WIDTH - 306, 86, 204, 128)
        pygame.draw.rect(self.screen, (34, 31, 37), prison_block, border_radius=10)
        pygame.draw.rect(self.screen, (92, 72, 68), prison_block, 2, border_radius=10)
        for column in range(4):
            cell = pygame.Rect(prison_block.x + 18 + column * 44, prison_block.y + 28, 28, 72)
            pygame.draw.rect(self.screen, (78, 42, 38), cell, border_radius=4)
            for bar_x in range(cell.left + 6, cell.right, 7):
                pygame.draw.line(self.screen, (186, 150, 124), (bar_x, cell.top + 4), (bar_x, cell.bottom - 4), 2)

        floor = pygame.Rect(0, settings.HEIGHT - 120, settings.WIDTH, 120)
        pygame.draw.rect(self.screen, (68, 52, 50), floor)
        pygame.draw.line(self.screen, (146, 113, 94), (0, floor.top + 4), (settings.WIDTH, floor.top + 4), 3)

        for vent_x in (186, 478, 786, 1092):
            vent = pygame.Rect(vent_x, settings.HEIGHT - 176, 76, 30)
            pygame.draw.rect(self.screen, (43, 38, 42), vent, border_radius=8)
            for index in range(4):
                steam = pygame.Surface((60, 80), pygame.SRCALPHA)
                offset_x = math.sin(ticks * 0.65 + vent_x + index) * 8
                offset_y = math.cos(ticks * 0.42 + index) * 4
                pygame.draw.ellipse(steam, (205, 198, 184, 30), pygame.Rect(0, 0, 42, 26))
                pygame.draw.ellipse(steam, (205, 198, 184, 24), pygame.Rect(16, 16, 34, 24))
                self.screen.blit(steam, (vent_x - 4 + offset_x, settings.HEIGHT - 236 - index * 22 + offset_y))

        spark_color = (255, 184, 92)
        for index in range(12):
            base_x = (index * 126 + ticks * 90) % settings.WIDTH
            base_y = 150 + (index % 4) * 118
            pygame.draw.line(self.screen, spark_color, (base_x, base_y), (base_x + 8, base_y + 14), 2)
            pygame.draw.line(self.screen, (255, 120, 76), (base_x + 2, base_y + 2), (base_x - 5, base_y + 18), 1)

    def draw_background(self) -> None:
        if self.level_data["world"] == 1:
            self.draw_world1_background()
        else:
            self.draw_world2_background()

        for platform in self.platforms:
            pygame.draw.rect(self.screen, self.theme["platform"], platform, border_radius=6)
            pygame.draw.rect(self.screen, self.theme["trim"], platform, 2, border_radius=6)

        princess_pos = self.level_data.get("princess_pos")
        if princess_pos:
            cage = pygame.Rect(princess_pos[0], princess_pos[1], 110, 138)
            pygame.draw.rect(self.screen, settings.PANEL, cage, border_radius=12)
            pygame.draw.rect(self.screen, self.theme["accent"] if self.ending_ready else settings.WARN, cage, 3, border_radius=12)
            for x in range(cage.left + 18, cage.right - 10, 18):
                pygame.draw.line(self.screen, settings.TEXT_COLOR, (x, cage.top + 14), (x, cage.bottom - 16), 3)
            if not self.ending_ready:
                princess = pygame.Rect(cage.centerx - 18, cage.bottom - 74, 36, 58)
                pygame.draw.rect(self.screen, settings.GOLD, princess, border_radius=8)
                pygame.draw.circle(self.screen, settings.TEXT_COLOR, (princess.centerx, princess.top + 10), 10)
            else:
                label = self.font_small.render("EMPTY", True, settings.WARN)
                self.screen.blit(label, label.get_rect(center=cage.center))

    def draw_hud(self) -> None:
        panel = pygame.Rect(20, settings.HEIGHT - settings.HUD_HEIGHT, settings.WIDTH - 40, settings.HUD_HEIGHT - 10)
        pygame.draw.rect(self.screen, settings.PANEL, panel, border_radius=14)
        pygame.draw.rect(self.screen, settings.PANEL_OUTLINE, panel, 2, border_radius=14)

        hp_bar = pygame.Rect(panel.left + 22, panel.top + 22, 260, 16)
        xp_bar = pygame.Rect(panel.left + 22, panel.top + 58, 260, 12)
        pygame.draw.rect(self.screen, (34, 38, 51), hp_bar, border_radius=8)
        pygame.draw.rect(self.screen, (34, 38, 51), xp_bar, border_radius=8)

        hp_fill = hp_bar.copy()
        hp_fill.width = int(hp_bar.width * max(0.0, self.player.hp / self.player.max_hp))
        pygame.draw.rect(self.screen, settings.WARN, hp_fill, border_radius=8)

        xp_fill = xp_bar.copy()
        xp_fill.width = int(xp_bar.width * min(1.0, self.player.xp / self.player.xp_to_next))
        pygame.draw.rect(self.screen, settings.ACCENT, xp_fill, border_radius=8)

        level = self.level_data
        weapon = settings.WEAPON_DATA[self.player.current_weapon_id]

        self.screen.blit(self.font_small.render(f"HP {int(self.player.hp)}/{self.player.max_hp}", True, settings.TEXT_COLOR), (hp_bar.left, hp_bar.top - 18))
        self.screen.blit(self.font_small.render(f"XP {self.player.xp}/{self.player.xp_to_next}", True, settings.TEXT_COLOR), (xp_bar.left, xp_bar.top - 18))
        self.screen.blit(self.font_medium.render(f"{self.theme['world_name']}  |  Level {level['level']}: {level['name']}", True, settings.TEXT_COLOR), (panel.left + 320, panel.top + 18))
        self.screen.blit(self.font_small.render(level["goal"], True, settings.SUBTEXT_COLOR), (panel.left + 320, panel.top + 52))
        self.screen.blit(self.font_medium.render(f"Weapon: {weapon['name']}", True, weapon["color"]), (panel.right - 300, panel.top + 18))
        self.screen.blit(
            self.font_small.render(
                f"Player Level {self.player.level}  |  Medkits: {self.player.items.get('medkit', 0)}  |  Press 1 to heal",
                True,
                settings.SUBTEXT_COLOR,
            ),
            (panel.right - 300, panel.top + 52),
        )

        statuses = self.player.powerup_status()
        if statuses:
            x = panel.left + 320
            y = panel.top + 78
            self.screen.blit(self.font_small.render("Power Ups:", True, settings.TEXT_COLOR), (x, y))
            x += 98
            for label, color in statuses:
                status_label = self.font_small.render(label, True, color)
                self.screen.blit(status_label, (x, y))
                x += status_label.get_width() + 18

        boss = next((enemy for enemy in self.enemies if enemy.is_boss), None)
        if boss:
            bar = pygame.Rect(settings.WIDTH // 2 - 190, 16, 380, 14)
            pygame.draw.rect(self.screen, (38, 32, 44), bar, border_radius=7)
            fill = bar.copy()
            fill.width = int(bar.width * max(0.0, boss.hp / boss.max_hp))
            pygame.draw.rect(self.screen, settings.WARN, fill, border_radius=7)
            label = self.font_small.render(boss.name, True, settings.TEXT_COLOR)
            self.screen.blit(label, label.get_rect(midbottom=(bar.centerx, bar.top - 4)))

    def draw_inventory(self) -> None:
        if not self.inventory_open:
            return

        panel = pygame.Rect(settings.WIDTH - 364, 72, 314, 392)
        pygame.draw.rect(self.screen, settings.PANEL, panel, border_radius=12)
        pygame.draw.rect(self.screen, settings.PANEL_OUTLINE, panel, 2, border_radius=12)
        self.screen.blit(self.font_medium.render("Inventory", True, settings.TEXT_COLOR), (panel.left + 18, panel.top + 18))

        y = panel.top + 56
        self.screen.blit(self.font_small.render("Weapons", True, settings.ACCENT), (panel.left + 18, y))
        y += 24
        for index, weapon_id in enumerate(self.player.weapons):
            weapon = settings.WEAPON_DATA[weapon_id]
            prefix = ">" if index == self.player.active_weapon else " "
            label = f"{prefix} {weapon['name']}"
            self.screen.blit(self.font_small.render(label, True, weapon["color"]), (panel.left + 24, y))
            y += 20
            for line in wrap_text(self.font_small, weapon["description"], panel.width - 42):
                self.screen.blit(self.font_small.render(line, True, settings.SUBTEXT_COLOR), (panel.left + 30, y))
                y += 18
            y += 8

        self.screen.blit(self.font_small.render("Items", True, settings.GOLD), (panel.left + 18, y))
        y += 24
        if not self.player.items:
            self.screen.blit(self.font_small.render("No items collected.", True, settings.SUBTEXT_COLOR), (panel.left + 24, y))
        else:
            for item_id, count in sorted(self.player.items.items()):
                item = settings.ITEM_DATA[item_id]
                self.screen.blit(self.font_small.render(f"{item['name']} x{count}", True, item["color"]), (panel.left + 24, y))
                y += 20
                for line in wrap_text(self.font_small, item["description"], panel.width - 42):
                    self.screen.blit(self.font_small.render(line, True, settings.SUBTEXT_COLOR), (panel.left + 30, y))
                    y += 18
                y += 8

    def draw_dialogue(self) -> None:
        if not self.story_dialogue:
            return

        panel = pygame.Rect(50, settings.HEIGHT - 214, settings.WIDTH - 100, 128)
        pygame.draw.rect(self.screen, settings.PANEL, panel, border_radius=14)
        pygame.draw.rect(self.screen, self.story_dialogue.accent, panel, 2, border_radius=14)
        self.screen.blit(self.font_medium.render(self.story_dialogue.speaker, True, self.story_dialogue.accent), (panel.left + 18, panel.top + 16))

        y = panel.top + 54
        for line in wrap_text(self.font_medium, self.story_dialogue.current_line, panel.width - 36):
            self.screen.blit(self.font_medium.render(line, True, settings.TEXT_COLOR), (panel.left + 18, y))
            y += 28
        prompt = self.font_small.render("Press Enter to continue", True, settings.SUBTEXT_COLOR)
        self.screen.blit(prompt, (panel.right - 208, panel.bottom - 28))

    def draw_pause_menu(self) -> None:
        if not self.pause_menu_open:
            return

        overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 158))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(settings.WIDTH / 2 - 230, 172, 460, 340)
        pygame.draw.rect(self.screen, settings.PANEL, panel, border_radius=16)
        pygame.draw.rect(self.screen, settings.PANEL_OUTLINE, panel, 2, border_radius=16)

        title = self.font_title.render("Paused", True, settings.TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(panel.centerx, panel.top + 52)))

        help_text = self.font_small.render("Use Up / Down and Enter. Press Tab to resume quickly.", True, settings.SUBTEXT_COLOR)
        self.screen.blit(help_text, help_text.get_rect(center=(panel.centerx, panel.top + 92)))

        y = panel.top + 138
        for index, option in enumerate(self.pause_options()):
            selected = index == self.pause_index
            color = settings.ACCENT if selected else settings.TEXT_COLOR
            prefix = "> " if selected else "  "
            label = self.font_large.render(f"{prefix}{option}", True, color)
            self.screen.blit(label, label.get_rect(center=(panel.centerx, y)))
            y += 46

        message = self.pause_message or "Saving keeps your current level, weapons, items, and enemy progress."
        color = settings.SUBTEXT_COLOR
        if self.pause_message == "Game saved.":
            color = settings.SUCCESS
        elif self.pause_message:
            color = settings.WARN
        note = self.font_small.render(message, True, color)
        self.screen.blit(note, note.get_rect(center=(panel.centerx, panel.bottom - 42)))

    def draw_world_select(self) -> None:
        ticks = pygame.time.get_ticks() / 1000.0
        self.screen.fill((235, 221, 192))

        for band, color in enumerate(((236, 217, 196), (226, 201, 189), (212, 179, 175))):
            rect = pygame.Rect(0, 120 + band * 168, settings.WIDTH, 170)
            pygame.draw.rect(self.screen, color, rect)

        cloud_surface = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
        cloud_color = (209, 175, 170, 112)
        cloud_centers = [
            (180, 96), (830, 76), (176, 236), (690, 282), (1102, 238), (744, 564),
        ]
        for index, (center_x, center_y) in enumerate(cloud_centers):
            drift = math.sin(ticks * 0.25 + index) * 16
            for offset_x, offset_y, width, height in ((-76, 18, 152, 58), (-8, 0, 184, 68), (84, 20, 146, 52)):
                ellipse = pygame.Rect(0, 0, width, height)
                ellipse.center = (center_x + offset_x + drift, center_y + offset_y)
                pygame.draw.ellipse(cloud_surface, cloud_color, ellipse)
        self.screen.blit(cloud_surface, (0, 0))

        horizon = pygame.Rect(0, settings.HEIGHT - 170, settings.WIDTH, 170)
        pygame.draw.rect(self.screen, (213, 182, 176), horizon)
        pygame.draw.line(self.screen, (236, 216, 199), (0, settings.HEIGHT - 186), (settings.WIDTH, settings.HEIGHT - 186), 3)

        def draw_silhouette_island(rect: pygame.Rect, selected: bool = False, accent: tuple[int, int, int] | None = None, locked: bool = False) -> None:
            body_color = (18, 20, 26) if not locked else (30, 28, 32)
            island = pygame.Rect(rect)
            pygame.draw.rect(self.screen, body_color, island, border_radius=10)
            top = island.inflate(-8, -island.height + 22)
            pygame.draw.rect(self.screen, body_color, top, border_radius=10)
            pygame.draw.circle(self.screen, body_color, (island.left + 54, island.top + 4), 24)
            pygame.draw.circle(self.screen, body_color, (island.left + 112, island.top + 2), 28)
            pygame.draw.circle(self.screen, body_color, (island.left + 148, island.top + 12), 20)
            if selected and accent:
                glow = pygame.Surface((island.width + 34, island.height + 34), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*accent, 84), glow.get_rect(), border_radius=18)
                self.screen.blit(glow, glow.get_rect(center=island.center))
                pygame.draw.rect(self.screen, accent, island.inflate(10, 10), 4, border_radius=14)

        decorative_islands = [
            pygame.Rect(214, 160, 220, 122),
            pygame.Rect(888, 182, 232, 128),
            pygame.Rect(430, 640, 212, 112),
        ]
        for rect in decorative_islands:
            draw_silhouette_island(rect, locked=True)

        world_positions = {
            1: pygame.Rect(118, 428, 206, 102),
            2: pygame.Rect(584, 372, 224, 106),
        }
        future_positions = [
            pygame.Rect(1062, 422, 186, 100),
            pygame.Rect(890, 182, 232, 128),
            pygame.Rect(430, 640, 212, 112),
        ]

        selectable = self.selectable_worlds()
        selected_world = selectable[self.world_select_index]
        for world_id in self.world_ids():
            rect = world_positions.get(world_id)
            if not rect:
                continue
            theme = settings.WORLD_THEMES[world_id]
            draw_silhouette_island(rect, selected=world_id == selected_world, accent=theme["accent"])
            label = self.font_small.render(f"World {world_id}", True, theme["accent"] if world_id == selected_world else settings.TEXT_COLOR)
            self.screen.blit(label, label.get_rect(center=(rect.centerx, rect.bottom + 28)))

        extra_locked = max(0, 5 - len(self.world_ids()))
        for rect in future_positions[:extra_locked]:
            draw_silhouette_island(rect, locked=True)

        title = self.font_title.render("World Selection", True, (63, 52, 48))
        self.screen.blit(title, title.get_rect(center=(settings.WIDTH / 2, 92)))
        subtitle = self.font_medium.render("Every five levels opens the next world route.", True, (111, 88, 84))
        self.screen.blit(subtitle, subtitle.get_rect(center=(settings.WIDTH / 2, 132)))

        selected_theme = settings.WORLD_THEMES[selected_world]
        selected_name = selected_theme["world_name"].split(": ", 1)[-1]
        first_level, last_level = self.level_range_for_world(selected_world)
        sign = pygame.Rect(44, settings.HEIGHT - 220, 294, 112)
        pygame.draw.rect(self.screen, (157, 116, 87), sign, border_radius=14)
        pygame.draw.rect(self.screen, (214, 188, 150), sign.inflate(-16, -16), border_radius=10)
        pygame.draw.rect(self.screen, selected_theme["accent"], sign, 4, border_radius=14)
        world_label = self.font_large.render(f"World {selected_world}", True, settings.GOLD)
        self.screen.blit(world_label, (sign.left + 20, sign.top + 18))
        name_label = self.font_medium.render(selected_name, True, (73, 55, 50))
        self.screen.blit(name_label, (sign.left + 20, sign.top + 50))
        range_label = self.font_small.render(f"Levels {first_level}-{last_level}", True, (92, 71, 66))
        self.screen.blit(range_label, (sign.left + 20, sign.top + 82))

        info_panel = pygame.Rect(settings.WIDTH - 420, settings.HEIGHT - 164, 364, 88)
        pygame.draw.rect(self.screen, (36, 32, 36), info_panel, border_radius=14)
        pygame.draw.rect(self.screen, selected_theme["accent"], info_panel, 2, border_radius=14)
        prompt = self.font_small.render("Use Left / Right to switch worlds. Press Enter to deploy.", True, settings.TEXT_COLOR)
        self.screen.blit(prompt, prompt.get_rect(center=(info_panel.centerx, info_panel.centery - 10)))
        unlocked = self.font_small.render(f"Unlocked Worlds: {self.max_world_unlocked}", True, settings.SUBTEXT_COLOR)
        self.screen.blit(unlocked, unlocked.get_rect(center=(info_panel.centerx, info_panel.centery + 18)))

    def draw_menu(self) -> None:
        self.draw_background()
        overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        title = self.font_title.render(settings.TITLE, True, settings.TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(settings.WIDTH / 2, 156)))
        subtitle = self.font_medium.render("Track Princess Elara through the first chapter", True, settings.GOLD)
        self.screen.blit(subtitle, subtitle.get_rect(center=(settings.WIDTH / 2, 208)))

        card = pygame.Rect(settings.WIDTH / 2 - 380, 248, 760, 356)
        pygame.draw.rect(self.screen, settings.PANEL, card, border_radius=18)
        pygame.draw.rect(self.screen, settings.PANEL_OUTLINE, card, 2, border_radius=18)

        lines = [
            "Two worlds, ten levels, and a boss every fifth stage.",
            "Every boss world opens a world-selection screen before the next route begins.",
            "Find new guns and blades hidden across platforms while climbing deeper into the base.",
            "Enemies shout taunts over their heads, and level 10 ends on a cliffhanger.",
            "Controls: move with A and D, jump with W or Up, attack with Space, use medkits with 1, inventory with I, and pause with Tab.",
        ]
        y = card.top + 28
        for line in lines:
            for wrapped in wrap_text(self.font_medium, line, card.width - 56):
                self.screen.blit(self.font_medium.render(wrapped, True, settings.TEXT_COLOR), (card.left + 28, y))
                y += 30
            y += 6

        load_available = save_exists()
        y += 14
        for index, option in enumerate(self.menu_options()):
            selected = index == self.menu_index
            if option == "Load Game" and not load_available:
                color = settings.GOLD if selected else settings.SUBTEXT_COLOR
            else:
                color = settings.ACCENT if selected else settings.TEXT_COLOR
            prefix = "> " if selected else "  "
            label = self.font_large.render(f"{prefix}{option}", True, color)
            self.screen.blit(label, (card.left + 36, y))
            if option == "Load Game":
                detail = "Save found" if load_available else "No save file yet"
                detail_label = self.font_small.render(detail, True, settings.SUBTEXT_COLOR)
                self.screen.blit(detail_label, (card.right - 176, y + 10))
            y += 42

        prompt = self.font_small.render("Use Up / Down and Enter to choose an option.", True, settings.SUBTEXT_COLOR)
        self.screen.blit(prompt, prompt.get_rect(center=(settings.WIDTH / 2, 630)))

        if self.menu_message:
            color = settings.WARN if "No save" in self.menu_message or "could not" in self.menu_message or "corrupted" in self.menu_message else settings.SUBTEXT_COLOR
            message = self.font_small.render(self.menu_message, True, color)
            self.screen.blit(message, message.get_rect(center=(settings.WIDTH / 2, 666)))

    def draw_gameover(self) -> None:
        self.draw_background()
        overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        title = self.font_title.render("Run Lost", True, settings.WARN)
        self.screen.blit(title, title.get_rect(center=(settings.WIDTH / 2, 208)))
        stats = [
            f"Reached Level {self.level_data['level']}: {self.level_data['name']}",
            f"Player Level {self.player.level}",
            f"Weapons Found: {len(self.player.weapons)}",
            f"Run Seed: {self.run_seed}",
        ]
        y = 292
        for line in stats:
            label = self.font_medium.render(line, True, settings.TEXT_COLOR)
            self.screen.blit(label, label.get_rect(center=(settings.WIDTH / 2, y)))
            y += 40
        prompt = self.font_large.render("Press Enter to return to the title screen", True, settings.GOLD)
        self.screen.blit(prompt, prompt.get_rect(center=(settings.WIDTH / 2, 530)))

    def draw_tbc(self) -> None:
        self.draw_background()
        overlay = pygame.Surface((settings.WIDTH, settings.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))
        title = self.font_title.render("To Be Continued", True, settings.GOLD)
        self.screen.blit(title, title.get_rect(center=(settings.WIDTH / 2, 196)))

        lines = [
            "Lord Malgrin is defeated, but Princess Elara is gone before you can reach her.",
            "The cage is empty and the Blackfang logs point toward a higher fortress.",
            f"Chapter 1 complete at player level {self.player.level}.",
            f"Weapons recovered: {', '.join(settings.WEAPON_DATA[weapon]['name'] for weapon in self.player.weapons)}.",
        ]
        y = 286
        for line in lines:
            for wrapped in wrap_text(self.font_medium, line, 760):
                label = self.font_medium.render(wrapped, True, settings.TEXT_COLOR)
                self.screen.blit(label, label.get_rect(center=(settings.WIDTH / 2, y)))
                y += 34
            y += 4
        prompt = self.font_large.render("Press Enter to return to the title screen", True, settings.ACCENT)
        self.screen.blit(prompt, prompt.get_rect(center=(settings.WIDTH / 2, 548)))

    def draw_playfield(self) -> None:
        self.draw_background()

        for pickup in self.pickups:
            pickup.draw(self.screen, self.font_small)
        for bullet in self.player_bullets:
            bullet.draw(self.screen)
        for bullet in self.enemy_bullets:
            bullet.draw(self.screen)
        for enemy in self.enemies:
            enemy.draw(self.screen, self.font_small)

        if self.slash_effect:
            slash = pygame.Surface((self.slash_effect["rect"].width, self.slash_effect["rect"].height), pygame.SRCALPHA)
            pygame.draw.rect(slash, (*self.slash_effect["color"], 90), slash.get_rect(), border_radius=10)
            self.screen.blit(slash, self.slash_effect["rect"])

        self.player.draw(self.screen)
        for text in self.floating_texts:
            text.draw(self.screen, self.font_small)

        if self.level_complete and not self.story_dialogue:
            if self.ending_ready:
                prompt = self.font_medium.render("The prison cell is empty. Press Enter to continue the story.", True, settings.GOLD)
            else:
                prompt = self.font_medium.render("Level clear. Press Enter to continue.", True, settings.SUCCESS)
            self.screen.blit(prompt, prompt.get_rect(center=(settings.WIDTH / 2, 108)))

        self.draw_hud()
        self.draw_inventory()
        self.draw_dialogue()
        self.draw_pause_menu()

    def draw(self) -> None:
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "world_select":
            self.draw_world_select()
        elif self.state == "gameover":
            self.draw_gameover()
        elif self.state == "tbc":
            self.draw_tbc()
        else:
            self.draw_playfield()

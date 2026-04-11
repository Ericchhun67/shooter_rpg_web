from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

import pygame

from game import settings

Vec2 = pygame.Vector2
Color = tuple[int, int, int]
PLAYER_SPRITE_PATH = Path(__file__).resolve().parent.parent / "assets" / "player" / "idle.png"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass
class FloatingText:
    text: str
    pos: Vec2
    color: Color
    life: float = 1.0
    drift: Vec2 = field(default_factory=lambda: Vec2(0, -32))

    def update(self, dt: float) -> bool:
        self.pos += self.drift * dt
        self.life -= dt
        return self.life > 0.0

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        alpha = max(0, min(255, int(255 * self.life)))
        label = font.render(self.text, True, self.color)
        label.set_alpha(alpha)
        surface.blit(label, label.get_rect(center=(self.pos.x, self.pos.y)))


@dataclass
class Bullet:
    pos: Vec2
    velocity: Vec2
    damage: float
    color: Color
    from_enemy: bool = False
    radius: int = 5
    life: float = 1.6

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.pos.x - self.radius), int(self.pos.y - self.radius), self.radius * 2, self.radius * 2)

    def update(self, dt: float, platforms: list[pygame.Rect]) -> bool:
        self.pos += self.velocity * dt
        self.life -= dt
        if self.life <= 0:
            return False
        if self.pos.x < -40 or self.pos.x > settings.WIDTH + 40 or self.pos.y < -40 or self.pos.y > settings.HEIGHT + 40:
            return False
        bullet_rect = self.rect
        return not any(bullet_rect.colliderect(platform) for platform in platforms)

    def draw(self, surface: pygame.Surface) -> None:
        if self.velocity.length_squared() > 0:
            tail = self.pos - self.velocity.normalize() * 14
            pygame.draw.line(surface, self.color, tail, self.pos, 3)
        pygame.draw.circle(surface, self.color, self.pos, self.radius)


@dataclass
class Pickup:
    pickup_type: str
    pickup_id: str
    rect: pygame.Rect
    color: Color
    label: str
    pulse: float = 0.0

    def update(self, dt: float) -> None:
        self.pulse += dt * 3.2

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        bob = int(round(pygame.math.Vector2(0, 1).rotate(self.pulse * 65).x * 4))
        draw_rect = self.rect.move(0, bob)
        glow = pygame.Surface((draw_rect.width + 22, draw_rect.height + 22), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*self.color, 80), glow.get_rect())
        surface.blit(glow, glow.get_rect(center=draw_rect.center))
        pygame.draw.rect(surface, self.color, draw_rect, border_radius=8)
        pygame.draw.rect(surface, (247, 250, 252), draw_rect.inflate(-8, -8), 2, border_radius=6)
        label = font.render(self.label, True, settings.TEXT_COLOR)
        surface.blit(label, label.get_rect(midbottom=(draw_rect.centerx, draw_rect.top - 6)))

    def to_save_data(self) -> dict:
        return {
            "pickup_type": self.pickup_type,
            "pickup_id": self.pickup_id,
            "rect": [self.rect.x, self.rect.y, self.rect.width, self.rect.height],
            "pulse": self.pulse,
        }

    @classmethod
    def from_save_data(cls, data: dict) -> "Pickup":
        if data["pickup_type"] == "weapon":
            entry = settings.WEAPON_DATA[data["pickup_id"]]
        elif data["pickup_type"] == "powerup":
            entry = settings.POWERUP_DATA[data["pickup_id"]]
        else:
            entry = settings.ITEM_DATA[data["pickup_id"]]
        rect = pygame.Rect(*data["rect"])
        pickup = cls(data["pickup_type"], data["pickup_id"], rect, entry["color"], entry["name"])
        pickup.pulse = float(data.get("pulse", 0.0))
        return pickup


class PhysicsActor:
    def __init__(self, x: float, y: float, width: int, height: int):
        self.pos = Vec2(x, y)
        self.rect = pygame.Rect(int(x), int(y), width, height)
        self.vel = Vec2()
        self.on_ground = False

    # Sync the rect position with the floating-point position
    def sync_rect(self) -> None:
        self.rect.x = int(round(self.pos.x))
        self.rect.y = int(round(self.pos.y))

    def move_and_collide(self, dt: float, platforms: list[pygame.Rect]) -> None:
        self.pos.x += self.vel.x * dt
        self.sync_rect()
        for platform in platforms:
            if self.rect.colliderect(platform):
                if self.vel.x > 0:
                    self.rect.right = platform.left
                elif self.vel.x < 0:
                    self.rect.left = platform.right
                self.pos.x = self.rect.x
                self.vel.x = 0

        self.vel.y += settings.GRAVITY * dt
        self.pos.y += self.vel.y * dt
        self.sync_rect()
        self.on_ground = False
        for platform in platforms:
            if self.rect.colliderect(platform):
                if self.vel.y > 0:
                    self.rect.bottom = platform.top
                    self.on_ground = True
                elif self.vel.y < 0:
                    self.rect.top = platform.bottom
                self.pos.y = self.rect.y
                self.vel.y = 0

        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(settings.WIDTH, self.rect.right)
        self.pos.x = self.rect.x


class Player(PhysicsActor):
    _sprite_cache: dict[str, pygame.Surface] | None = None

    def __init__(self, x: float, y: float):
        super().__init__(x, y, 42, 58)
        self.max_hp = 140
        self.hp = float(self.max_hp)
        self.level = 1
        self.xp = 0
        self.xp_to_next = 75
        self.attack_timer = 0.0
        self.invulnerable_timer = 0.0
        self.swing_timer = 0.0
        self.facing = 1
        self.weapons: list[str] = ["rust_pistol"]
        self.active_weapon = 0
        self.items: dict[str, int] = {"medkit": 2}
        self.aim_vector = Vec2(1, 0)
        self.powerup_timers: dict[str, float] = {powerup_id: 0.0 for powerup_id in settings.POWERUP_DATA}
        self.shield_hp = 0.0
        self.sprite_offset = Vec2(0, -4)
        self.sprites = self.load_sprites()

    @classmethod
    def load_sprites(cls) -> dict[str, pygame.Surface]:
        if cls._sprite_cache is not None:
            return cls._sprite_cache

        sprites: dict[str, pygame.Surface] = {}
        try:
            idle = pygame.image.load(PLAYER_SPRITE_PATH).convert_alpha()
            scaled = pygame.transform.scale(idle, (idle.get_width() * 2, idle.get_height() * 2))
            sprites["right"] = scaled
            sprites["left"] = pygame.transform.flip(scaled, True, False)
        except (FileNotFoundError, pygame.error):
            sprites = {}

        cls._sprite_cache = sprites
        return sprites

    @property
    def current_weapon_id(self) -> str:
        return self.weapons[self.active_weapon]

    @property
    def current_weapon(self) -> dict:
        return settings.WEAPON_DATA[self.current_weapon_id]

    def set_spawn(self, x: float, y: float) -> None:
        self.pos.update(x, y)
        self.vel.update(0, 0)
        self.sync_rect()

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper, platforms: list[pygame.Rect], mouse_pos: tuple[int, int]) -> None:
        for powerup_id in self.powerup_timers:
            self.powerup_timers[powerup_id] = max(0.0, self.powerup_timers[powerup_id] - dt)
        if self.powerup_timers.get("shield", 0.0) <= 0.0:
            self.shield_hp = 0.0

        move = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move += 1
        speed_scale = settings.POWERUP_DATA["speed_boost"]["speed_scale"] if self.has_powerup("speed_boost") else 1.0
        self.vel.x = move * settings.PLAYER_SPEED * speed_scale
        if move:
            self.facing = 1 if move > 0 else -1

        aim = Vec2(mouse_pos) - Vec2(self.rect.center)
        if aim.length_squared() > 1:
            self.aim_vector = aim.normalize()
            if abs(self.aim_vector.x) > 0.1:
                self.facing = 1 if self.aim_vector.x > 0 else -1

        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        self.swing_timer = max(0.0, self.swing_timer - dt)
        self.move_and_collide(dt, platforms)

    def jump(self) -> None:
        if self.on_ground:
            self.vel.y = settings.PLAYER_JUMP
            self.on_ground = False

    def attack(self, mouse_pos: tuple[int, int]) -> tuple[list[Bullet], pygame.Rect | None, float, Color | None]:
        if self.attack_timer > 0.0:
            return [], None, 0.0, None

        weapon = self.current_weapon
        cooldown = weapon["cooldown"]
        damage = weapon["damage"]
        if weapon["type"] == "gun" and self.has_powerup("gun_boost"):
            cooldown *= settings.POWERUP_DATA["gun_boost"]["cooldown_scale"]
            damage *= settings.POWERUP_DATA["gun_boost"]["damage_scale"]
        self.attack_timer = cooldown
        aim = Vec2(mouse_pos) - Vec2(self.rect.center)
        if aim.length_squared() <= 1:
            aim = Vec2(self.facing, 0)
        else:
            aim = aim.normalize()
        self.aim_vector = aim
        if abs(aim.x) > 0.1:
            self.facing = 1 if aim.x > 0 else -1

        if weapon["type"] == "gun":
            bullets: list[Bullet] = []
            for _ in range(weapon["pellets"]):
                direction = aim.rotate_rad(random.uniform(-weapon["spread"], weapon["spread"]))
                bullets.append(
                    Bullet(
                        Vec2(self.rect.centerx + self.facing * 18, self.rect.centery - 10),
                        direction * weapon["projectile_speed"],
                        damage,
                        weapon["color"],
                        from_enemy=False,
                    )
                )
            return bullets, None, 0.0, None

        self.swing_timer = 0.18
        hitbox = pygame.Rect(0, 0, weapon["range"], self.rect.height - 4)
        if self.facing > 0:
            hitbox.midleft = (self.rect.right - 2, self.rect.centery)
        else:
            hitbox.midright = (self.rect.left + 2, self.rect.centery)
        return [], hitbox, damage, weapon["color"]

    def receive_damage(self, amount: float) -> tuple[str, float]:
        if self.invulnerable_timer > 0.0:
            return "none", 0.0
        if self.has_powerup("shield") and self.shield_hp > 0.0:
            absorbed = min(self.shield_hp, amount)
            self.shield_hp = max(0.0, self.shield_hp - absorbed)
            remaining = amount - absorbed
            if self.shield_hp <= 0.0:
                self.powerup_timers["shield"] = 0.0
            if remaining <= 0.0:
                self.invulnerable_timer = 0.38
                return "shield", absorbed
            self.hp = max(0.0, self.hp - remaining)
            self.invulnerable_timer = 0.65
            return "hp", remaining
        self.hp = max(0.0, self.hp - amount)
        self.invulnerable_timer = 0.65
        return "hp", amount

    def gain_xp(self, amount: int) -> int:
        self.xp += amount
        levels = 0
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            levels += 1
            self.max_hp += 12
            self.hp = min(self.max_hp, self.hp + 24)
            self.xp_to_next = int(self.xp_to_next * 1.22 + 18)
        return levels

    def add_weapon(self, weapon_id: str) -> bool:
        if weapon_id in self.weapons:
            return False
        self.weapons.append(weapon_id)
        self.active_weapon = len(self.weapons) - 1
        return True

    def cycle_weapon(self, step: int) -> None:
        if not self.weapons:
            return
        self.active_weapon = (self.active_weapon + step) % len(self.weapons)

    def add_item(self, item_id: str, amount: int = 1) -> None:
        self.items[item_id] = self.items.get(item_id, 0) + amount

    def use_medkit(self) -> bool:
        if self.items.get("medkit", 0) <= 0 or self.hp >= self.max_hp:
            return False
        self.items["medkit"] -= 1
        if self.items["medkit"] <= 0:
            self.items.pop("medkit")
        self.hp = min(float(self.max_hp), self.hp + 50.0)
        return True

    def has_powerup(self, powerup_id: str) -> bool:
        return self.powerup_timers.get(powerup_id, 0.0) > 0.0

    def activate_powerup(self, powerup_id: str) -> None:
        powerup = settings.POWERUP_DATA[powerup_id]
        self.powerup_timers[powerup_id] = powerup["duration"]
        if powerup_id == "shield":
            self.shield_hp = powerup["shield_hp"]

    def powerup_status(self) -> list[tuple[str, Color]]:
        statuses: list[tuple[str, Color]] = []
        for powerup_id, timer in self.powerup_timers.items():
            if timer <= 0.0:
                continue
            powerup = settings.POWERUP_DATA[powerup_id]
            if powerup_id == "shield":
                statuses.append((f"{powerup['name']} {int(self.shield_hp)}", powerup["color"]))
            else:
                statuses.append((f"{powerup['name']} {timer:.1f}s", powerup["color"]))
        return statuses

    def draw(self, surface: pygame.Surface) -> None:
        flash = self.invulnerable_timer > 0 and int(self.invulnerable_timer * 16) % 2 == 0
        body = (241, 244, 248) if not flash else (140, 206, 255)
        suit = (36, 58, 92)
        visor = settings.ACCENT

        if self.has_powerup("shield"):
            shield = pygame.Surface((self.rect.width + 34, self.rect.height + 26), pygame.SRCALPHA)
            pygame.draw.ellipse(shield, (*settings.POWERUP_DATA["shield"]["color"], 56), shield.get_rect(), 4)
            surface.blit(shield, shield.get_rect(center=self.rect.center))
        if self.has_powerup("speed_boost"):
            for offset in (0, 8, 16):
                start = (self.rect.centerx - self.facing * (20 + offset), self.rect.centery + 4 - offset // 4)
                end = (self.rect.centerx - self.facing * (6 + offset), self.rect.centery + 10 - offset // 4)
                pygame.draw.line(surface, settings.POWERUP_DATA["speed_boost"]["color"], start, end, 3)

        shadow = pygame.Surface((self.rect.width + 26, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 78), shadow.get_rect())
        surface.blit(shadow, shadow.get_rect(center=(self.rect.centerx, self.rect.bottom + 6)))

        sprite = self.sprites.get("right" if self.facing >= 0 else "left")
        if sprite:
            draw_sprite = sprite
            if flash:
                draw_sprite = sprite.copy()
                draw_sprite.fill((120, 208, 255, 110), special_flags=pygame.BLEND_RGBA_ADD)
            sprite_rect = draw_sprite.get_rect(midbottom=(self.rect.centerx + self.sprite_offset.x, self.rect.bottom + self.sprite_offset.y))
            surface.blit(draw_sprite, sprite_rect)
        else:
            pygame.draw.rect(surface, body, self.rect, border_radius=10)
            chest = self.rect.inflate(-14, -18)
            pygame.draw.rect(surface, suit, chest, border_radius=8)
            visor_rect = pygame.Rect(self.rect.x + 8, self.rect.y + 10, self.rect.width - 16, 10)
            pygame.draw.rect(surface, visor, visor_rect, border_radius=5)

        weapon = self.current_weapon
        hand_y = self.rect.y + 24
        if weapon["type"] == "gun":
            muzzle = Vec2(self.rect.centerx + self.facing * 18, hand_y)
            aim = self.aim_vector if self.aim_vector.length_squared() > 0 else Vec2(self.facing, 0)
            gun_end = muzzle + aim * 18
            pygame.draw.line(surface, weapon["color"], muzzle, gun_end, 5)
            if self.has_powerup("gun_boost"):
                pygame.draw.circle(surface, settings.POWERUP_DATA["gun_boost"]["color"], gun_end, 6)
        else:
            hilt = Vec2(self.rect.centerx + self.facing * 10, hand_y)
            swing = 14 if self.swing_timer > 0 else 6
            blade_tip = hilt + Vec2(self.facing * (18 + swing), -12)
            pygame.draw.line(surface, weapon["color"], hilt, blade_tip, 6)

    def to_save_data(self) -> dict:
        return {
            "pos": [self.pos.x, self.pos.y],
            "vel": [self.vel.x, self.vel.y],
            "hp": self.hp,
            "max_hp": self.max_hp,
            "level": self.level,
            "xp": self.xp,
            "xp_to_next": self.xp_to_next,
            "attack_timer": self.attack_timer,
            "invulnerable_timer": self.invulnerable_timer,
            "swing_timer": self.swing_timer,
            "facing": self.facing,
            "weapons": list(self.weapons),
            "active_weapon": self.active_weapon,
            "items": dict(self.items),
            "aim_vector": [self.aim_vector.x, self.aim_vector.y],
            "on_ground": self.on_ground,
            "powerup_timers": dict(self.powerup_timers),
            "shield_hp": self.shield_hp,
        }

    def apply_save_data(self, data: dict) -> None:
        self.pos.update(*data["pos"])
        self.vel.update(*data.get("vel", (0.0, 0.0)))
        self.sync_rect()
        self.hp = float(data["hp"])
        self.max_hp = int(data["max_hp"])
        self.level = int(data["level"])
        self.xp = int(data["xp"])
        self.xp_to_next = int(data["xp_to_next"])
        self.attack_timer = float(data.get("attack_timer", 0.0))
        self.invulnerable_timer = float(data.get("invulnerable_timer", 0.0))
        self.swing_timer = float(data.get("swing_timer", 0.0))
        self.facing = int(data.get("facing", 1))
        self.weapons = list(data.get("weapons", ["rust_pistol"]))
        self.active_weapon = max(0, min(int(data.get("active_weapon", 0)), len(self.weapons) - 1))
        self.items = {item_id: int(amount) for item_id, amount in data.get("items", {}).items()}
        self.aim_vector = Vec2(data.get("aim_vector", (self.facing, 0)))
        if self.aim_vector.length_squared() <= 0:
            self.aim_vector = Vec2(self.facing or 1, 0)
        self.on_ground = bool(data.get("on_ground", False))
        saved_timers = data.get("powerup_timers", {})
        self.powerup_timers = {
            powerup_id: float(saved_timers.get(powerup_id, 0.0))
            for powerup_id in settings.POWERUP_DATA
        }
        self.shield_hp = float(data.get("shield_hp", 0.0))


class Enemy(PhysicsActor):
    def __init__(self, kind: str, x: float, y: float, line: str, patrol: tuple[int, int] | None = None, name: str | None = None):
        data = settings.ENEMY_DATA[kind]
        width, height = data["size"]
        super().__init__(x, y, width, height)
        self.kind = kind
        self.data = data
        self.name = name or data["name"]
        self.max_hp = data["max_hp"]
        self.hp = float(self.max_hp)
        self.speed = data["speed"]
        self.damage = data["damage"]
        self.xp_reward = data["xp"]
        self.fire_delay = data["fire_delay"]
        self.fire_timer = random.uniform(0.3, self.fire_delay if self.fire_delay < 90 else 1.0)
        self.jump_timer = random.uniform(1.0, 2.0)
        self.facing = -1
        self.patrol = patrol
        self.patrol_dir = 1
        self.speech = line
        self.speech_timer = 2.3
        self.taunt_timer = random.uniform(4.2, 7.0)
        self.flash = 0.0

    @property
    def is_boss(self) -> bool:
        return self.data["boss"]

    def set_speech(self, text: str, duration: float = 1.8) -> None:
        self.speech = text
        self.speech_timer = duration

    def hit(self, damage: float) -> None:
        self.hp -= damage
        self.flash = 0.8

    def blocks_projectile(self, bullet: Bullet) -> bool:
        if self.kind != "riot_guard":
            return False
        if self.facing > 0:
            return bullet.pos.x <= self.rect.centerx
        return bullet.pos.x >= self.rect.centerx

    def update(self, dt: float, player: Player, platforms: list[pygame.Rect]) -> list[Bullet]:
        self.flash = max(0.0, self.flash - dt * 4.0)
        self.speech_timer = max(0.0, self.speech_timer - dt)
        self.taunt_timer -= dt
        self.fire_timer = max(0.0, self.fire_timer - dt)
        self.jump_timer = max(0.0, self.jump_timer - dt)

        bullets: list[Bullet] = []
        player_center = Vec2(player.rect.center)
        my_center = Vec2(self.rect.center)
        offset = player_center - my_center
        distance = offset.length() if offset.length_squared() > 0 else 0.0
        direction = offset.normalize() if offset.length_squared() > 1 else Vec2(self.facing, 0)
        if abs(direction.x) > 0.1:
            self.facing = 1 if direction.x > 0 else -1

        aggressive = distance <= self.data["aggro"]

        if self.kind in {"guard", "hound", "crawler_drone", "flame_hound", "riot_guard"}:
            if self.kind == "riot_guard":
                if aggressive and distance > 116:
                    self.vel.x = self.facing * self.speed
                elif aggressive:
                    self.vel.x = 0
                elif self.patrol:
                    if self.rect.left <= self.patrol[0]:
                        self.patrol_dir = 1
                    elif self.rect.right >= self.patrol[1]:
                        self.patrol_dir = -1
                    self.vel.x = self.patrol_dir * self.speed * 0.5
                else:
                    self.vel.x = 0
            elif aggressive:
                self.vel.x = self.facing * self.speed
            elif self.patrol:
                if self.rect.left <= self.patrol[0]:
                    self.patrol_dir = 1
                elif self.rect.right >= self.patrol[1]:
                    self.patrol_dir = -1
                self.vel.x = self.patrol_dir * self.speed * 0.65
            else:
                self.vel.x = 0

            if self.kind in {"hound", "flame_hound"} and aggressive and self.on_ground and self.jump_timer <= 0 and player.rect.top < self.rect.top - 8:
                self.vel.y = -620 if self.kind == "hound" else -660
                self.jump_timer = random.uniform(1.4, 2.4) if self.kind == "hound" else random.uniform(1.0, 1.9)

        elif self.kind in {"gunner", "turret", "shock_engineer"}:
            if self.kind == "gunner":
                if aggressive and distance > 260:
                    self.vel.x = self.facing * self.speed
                elif aggressive and distance < 160:
                    self.vel.x = -self.facing * self.speed * 0.8
                elif self.patrol:
                    if self.rect.left <= self.patrol[0]:
                        self.patrol_dir = 1
                    elif self.rect.right >= self.patrol[1]:
                        self.patrol_dir = -1
                    self.vel.x = self.patrol_dir * self.speed * 0.45
                else:
                    self.vel.x = 0
            elif self.kind == "shock_engineer":
                if aggressive and distance > 280:
                    self.vel.x = self.facing * self.speed
                elif aggressive and distance < 184:
                    self.vel.x = -self.facing * self.speed * 0.72
                elif self.patrol:
                    if self.rect.left <= self.patrol[0]:
                        self.patrol_dir = 1
                    elif self.rect.right >= self.patrol[1]:
                        self.patrol_dir = -1
                    self.vel.x = self.patrol_dir * self.speed * 0.4
                else:
                    self.vel.x = 0
            else:
                self.vel.x = 0

            if aggressive and self.fire_timer <= 0.0:
                self.fire_timer = self.fire_delay
                shot_dir = direction if direction.length_squared() > 0 else Vec2(self.facing, 0)
                if self.kind == "shock_engineer":
                    for spread in (-0.12, 0.12):
                        bullets.append(
                            Bullet(
                                Vec2(self.rect.centerx + self.facing * 18, self.rect.centery - 10),
                                shot_dir.rotate_rad(spread) * 560,
                                self.damage,
                                self.data["color"],
                                from_enemy=True,
                                radius=6,
                            )
                        )
                else:
                    bullets.append(
                        Bullet(
                            Vec2(self.rect.centerx + self.facing * 18, self.rect.centery - 10),
                            shot_dir * 620,
                            self.damage,
                            (255, 196, 120) if self.kind == "gunner" else (120, 210, 255),
                            from_enemy=True,
                        )
                    )

        else:
            patrol_left, patrol_right = self.patrol if self.patrol else (80, settings.WIDTH - 80)
            if self.rect.left <= patrol_left:
                self.patrol_dir = 1
            elif self.rect.right >= patrol_right:
                self.patrol_dir = -1

            if aggressive:
                self.vel.x = self.facing * self.speed
            else:
                self.vel.x = self.patrol_dir * self.speed * 0.7

            if self.on_ground and self.jump_timer <= 0 and player.rect.top + 12 < self.rect.top:
                self.vel.y = -690
                self.jump_timer = random.uniform(1.4, 2.3)

            if self.fire_timer <= 0.0:
                self.fire_timer = self.fire_delay
                spreads = (-0.18, 0.0, 0.18) if self.kind == "thorn_warden" else (-0.28, -0.12, 0.0, 0.12, 0.28)
                speed = 660 if self.kind == "thorn_warden" else 720
                for spread in spreads:
                    bullets.append(
                        Bullet(
                            Vec2(self.rect.centerx + self.facing * 20, self.rect.centery - 14),
                            direction.rotate_rad(spread) * speed,
                            self.damage,
                            self.data["color"],
                            from_enemy=True,
                            radius=6,
                        )
                    )

        if aggressive and self.taunt_timer <= 0:
            self.set_speech(random.choice(settings.ENEMY_TAUNTS[self.kind]))
            self.taunt_timer = random.uniform(4.5, 7.5)

        self.move_and_collide(dt, platforms)
        return bullets

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        flash_mix = min(1.0, self.flash)
        body = tuple(min(255, int(channel + (255 - channel) * flash_mix * 0.5)) for channel in self.data["color"])
        shadow = pygame.Surface((self.rect.width + 24, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 76), shadow.get_rect())
        surface.blit(shadow, shadow.get_rect(center=(self.rect.centerx, self.rect.bottom + 6)))

        if self.kind in {"hound", "flame_hound"}:
            pygame.draw.ellipse(surface, body, self.rect)
            pygame.draw.ellipse(surface, self.data["secondary"], self.rect.inflate(-12, -12))
            if self.kind == "flame_hound":
                for index in range(3):
                    flame_x = self.rect.left + 10 + index * 12
                    flame_y = self.rect.top - 6 + (index % 2) * 3
                    pygame.draw.circle(surface, (255, 190, 94), (flame_x, flame_y), 5)
                    pygame.draw.circle(surface, (255, 116, 74), (flame_x, flame_y + 3), 4)
        elif self.kind == "crawler_drone":
            body_rect = self.rect.inflate(0, -4)
            pygame.draw.rect(surface, body, body_rect, border_radius=8)
            eye = pygame.Rect(body_rect.centerx - 10, body_rect.y + 8, 20, 6)
            pygame.draw.rect(surface, self.data["secondary"], eye, border_radius=3)
            for leg_x in (body_rect.left + 6, body_rect.left + 16, body_rect.right - 16, body_rect.right - 6):
                pygame.draw.line(surface, (45, 46, 56), (leg_x, body_rect.bottom - 2), (leg_x - 4 if leg_x < body_rect.centerx else leg_x + 4, body_rect.bottom + 8), 3)
        elif self.kind == "turret":
            base = self.rect.inflate(0, 6)
            pygame.draw.rect(surface, body, base, border_radius=8)
            turret_rect = pygame.Rect(self.rect.centerx - 8, self.rect.y - 8, 16, 20)
            pygame.draw.rect(surface, self.data["secondary"], turret_rect, border_radius=6)
            muzzle = Vec2(turret_rect.centerx + self.facing * 18, turret_rect.centery)
            pygame.draw.line(surface, settings.TEXT_COLOR, turret_rect.center, muzzle, 5)
        elif self.kind == "riot_guard":
            pygame.draw.rect(surface, body, self.rect, border_radius=10)
            chest = self.rect.inflate(-14, -18)
            pygame.draw.rect(surface, self.data["secondary"], chest, border_radius=8)
            shield_width = 18
            shield = pygame.Rect(0, 0, shield_width, self.rect.height - 6)
            if self.facing > 0:
                shield.midleft = (self.rect.right - 4, self.rect.centery)
            else:
                shield.midright = (self.rect.left + 4, self.rect.centery)
            pygame.draw.rect(surface, (210, 198, 168), shield, border_radius=8)
            pygame.draw.rect(surface, (98, 86, 68), shield.inflate(-8, -10), border_radius=6)
        elif self.kind == "shock_engineer":
            pygame.draw.rect(surface, body, self.rect, border_radius=10)
            chest = self.rect.inflate(-14, -18)
            pygame.draw.rect(surface, self.data["secondary"], chest, border_radius=8)
            coil_center = (self.rect.centerx + self.facing * 8, self.rect.y + 12)
            pygame.draw.circle(surface, settings.TEXT_COLOR, coil_center, 8, 2)
            pygame.draw.circle(surface, body, coil_center, 4)
        else:
            pygame.draw.rect(surface, body, self.rect, border_radius=10)
            chest = self.rect.inflate(-12, -18)
            pygame.draw.rect(surface, self.data["secondary"], chest, border_radius=8)

        if self.hp < self.max_hp:
            bar = pygame.Rect(self.rect.left, self.rect.top - 12, self.rect.width, 6)
            pygame.draw.rect(surface, (32, 32, 40), bar, border_radius=3)
            fill = bar.copy()
            fill.width = int(bar.width * max(0.0, self.hp / self.max_hp))
            pygame.draw.rect(surface, settings.WARN if self.is_boss else settings.SUCCESS, fill, border_radius=3)

        if self.speech_timer > 0 and self.speech:
            bubble = font.render(self.speech, True, settings.TEXT_COLOR)
            bubble_rect = bubble.get_rect(midbottom=(self.rect.centerx, self.rect.top - 18))
            panel = bubble_rect.inflate(18, 10)
            pygame.draw.rect(surface, settings.PANEL, panel, border_radius=8)
            pygame.draw.rect(surface, self.data["color"], panel, 2, border_radius=8)
            surface.blit(bubble, bubble_rect)

    def to_save_data(self) -> dict:
        return {
            "kind": self.kind,
            "name": self.name,
            "pos": [self.pos.x, self.pos.y],
            "vel": [self.vel.x, self.vel.y],
            "hp": self.hp,
            "patrol": list(self.patrol) if self.patrol else None,
            "speech": self.speech,
            "speech_timer": self.speech_timer,
            "taunt_timer": self.taunt_timer,
            "fire_timer": self.fire_timer,
            "jump_timer": self.jump_timer,
            "facing": self.facing,
            "flash": self.flash,
            "patrol_dir": self.patrol_dir,
            "on_ground": self.on_ground,
        }

    @classmethod
    def from_save_data(cls, data: dict) -> "Enemy":
        patrol = tuple(data["patrol"]) if data.get("patrol") else None
        enemy = cls(
            data["kind"],
            data["pos"][0],
            data["pos"][1],
            data.get("speech", ""),
            patrol,
            data.get("name"),
        )
        enemy.vel.update(*data.get("vel", (0.0, 0.0)))
        enemy.sync_rect()
        enemy.hp = float(data["hp"])
        enemy.speech = data.get("speech", "")
        enemy.speech_timer = float(data.get("speech_timer", 0.0))
        enemy.taunt_timer = float(data.get("taunt_timer", enemy.taunt_timer))
        enemy.fire_timer = float(data.get("fire_timer", enemy.fire_timer))
        enemy.jump_timer = float(data.get("jump_timer", enemy.jump_timer))
        enemy.facing = int(data.get("facing", enemy.facing))
        enemy.flash = float(data.get("flash", 0.0))
        enemy.patrol_dir = int(data.get("patrol_dir", enemy.patrol_dir))
        enemy.on_ground = bool(data.get("on_ground", False))
        return enemy

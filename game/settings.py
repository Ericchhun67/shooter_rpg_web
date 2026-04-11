from __future__ import annotations

TITLE = "Riftbreaker Protocol"
WIDTH = 1380
HEIGHT = 820
FPS = 60 # Target frames per second for the game loop

GRAVITY = 1900
PLAYER_SPEED = 315
PLAYER_JUMP = -760

HUD_HEIGHT = 108

BG_COLOR = (11, 13, 20)
TEXT_COLOR = (239, 243, 249)
SUBTEXT_COLOR = (144, 162, 187)
PANEL = (15, 20, 31)
PANEL_OUTLINE = (55, 77, 107)
ACCENT = (93, 199, 255)
WARN = (248, 102, 102)
SUCCESS = (106, 223, 137)
GOLD = (247, 204, 92)
PURPLE = (155, 133, 255)

# Data structures for defining enemies, weapons, items, and levels. These are used to populate the game world and can be easily modified or expanded for future content updates.
def enemy(kind: str, x: int, y: int, line: str, patrol: tuple[int, int] | None = None, name: str | None = None) -> dict:
    return {"kind": kind, "x": x, "y": y, "line": line, "patrol": patrol, "name": name}


def weapon_pickup(weapon_id: str, x: int, y: int) -> dict:
    """ 
    weapon_id: str - The identifier for the weapon being picked up (e.g., 
    "rust_pistol", "iron_saber").
    x: int - The x-coordinate of the weapon pickup location in the game world.
    y: int - The y-coordinate of the weapon pickup location in the game world.
    """
    return {"weapon_id": weapon_id, "x": x, "y": y}


def item_pickup(item_id: str, x: int, y: int) -> dict:
    return {"item_id": item_id, "x": x, "y": y}


POWERUP_DATA = {
    "shield": {
        "name": "Shield Cell",
        "color": ACCENT,
        "description": "Projects a barrier that absorbs 60 damage for 12 seconds.",
        "duration": 12.0,
        "shield_hp": 60.0,
    },
    "gun_boost": {
        "name": "Gun Boost",
        "color": GOLD,
        "description": "Gun damage surges and fire rate increases for 10 seconds.",
        "duration": 10.0,
        "damage_scale": 1.55,
        "cooldown_scale": 0.72,
    },
    "speed_boost": {
        "name": "Speed Boost",
        "color": SUCCESS,
        "description": "Movement speed rises sharply for 9 seconds.",
        "duration": 9.0,
        "speed_scale": 1.24,
    },
}

POWERUP_DROP_POOL = ["shield", "gun_boost", "speed_boost"]
POWERUP_DROP_WEIGHTS = [3, 4, 3]
POWERUP_DROP_CHANCE = 0.2
BOSS_POWERUP_DROP_CHANCE = 0.7


WEAPON_DATA = {
    "rust_pistol": {
        "name": "Rust Pistol",
        "type": "gun",
        "damage": 18,
        "cooldown": 0.28,
        "projectile_speed": 880,
        "pellets": 1,
        "spread": 0.03,
        "color": ACCENT,
        "description": "Reliable starter sidearm with balanced range and damage.",
    },
    "iron_saber": {
        "name": "Iron Saber",
        "type": "melee",
        "damage": 34,
        "cooldown": 0.34,
        "range": 84,
        "color": (215, 225, 236),
        "description": "A heavy sword with strong close-range burst damage.",
    },
    "burst_rifle": {
        "name": "Burst Rifle",
        "type": "gun",
        "damage": 12,
        "cooldown": 0.14,
        "projectile_speed": 980,
        "pellets": 1,
        "spread": 0.02,
        "color": GOLD,
        "description": "Fast firing rifle that rewards sustained pressure.",
    },
    "scattergun": {
        "name": "Scattergun",
        "type": "gun",
        "damage": 13,
        "cooldown": 0.58,
        "projectile_speed": 760,
        "pellets": 5,
        "spread": 0.22,
        "color": WARN,
        "description": "Wide burst shotgun that dominates close platforms.",
    },
    "royal_blade": {
        "name": "Royal Blade",
        "type": "melee",
        "damage": 52,
        "cooldown": 0.24,
        "range": 96,
        "color": PURPLE,
        "description": "A fast enchanted sword once carried by the royal guard.",
    },
    "plasma_carbine": {
        "name": "Plasma Carbine",
        "type": "gun",
        "damage": 16,
        "cooldown": 0.11,
        "projectile_speed": 1040,
        "pellets": 1,
        "spread": 0.01,
        "color": SUCCESS,
        "description": "Late-game rifle with speed and precision for the final base.",
    },
    "plasma_raygun": {
        "name": "Plasma Raygun",
        "type": "gun",
        "damage": 8,
        "cooldown": 0.04,
        "projectile_speed": 1280,
        "pellets": 1,
        "spread": 0.0,
        "color": (255, 112, 112),
        "description": "Experimental rapid-fire weapon that shoots superheated plasma.",
    },
}

ITEM_DATA = {
    "medkit": {
        "name": "Medkit",
        "color": SUCCESS,
        "description": "Restores 50 HP. Press 1 to use one.",
    },
    "alloy_scrap": {
        "name": "Alloy Scrap",
        "color": (171, 181, 195),
        "description": "Broken machine parts scavenged from fallen troops.",
    },
    "prison_key": {
        "name": "Prison Key",
        "color": GOLD,
        "description": "A brass security key stamped with the Blackfang crest.",
    },
    "royal_seal": {
        "name": "Royal Seal",
        "color": PURPLE,
        "description": "A signet recovered from the route to Princess Elara.",
    },
    "warden_core": {
        "name": "Warden Core",
        "color": WARN,
        "description": "A boss core that hums with corrupt base energy.",
    },
}

ENEMY_DATA = {
    "guard": {
        "name": "Blackfang Guard",
        "size": (42, 54),
        "max_hp": 70,
        "speed": 145,
        "damage": 14,
        "xp": 24,
        "color": (220, 90, 90),
        "secondary": (255, 214, 148),
        "aggro": 320,
        "fire_delay": 99.0,
        "boss": False,
    },
    "gunner": {
        "name": "Sentry Gunner",
        "size": (44, 56),
        "max_hp": 92,
        "speed": 118,
        "damage": 11,
        "xp": 34,
        "color": (255, 175, 86),
        "secondary": (66, 43, 28),
        "aggro": 540,
        "fire_delay": 1.2,
        "boss": False,
    },
    "hound": {
        "name": "Rift Hound",
        "size": (46, 40),
        "max_hp": 78,
        "speed": 210,
        "damage": 16,
        "xp": 28,
        "color": (116, 216, 160),
        "secondary": (36, 68, 57),
        "aggro": 290,
        "fire_delay": 99.0,
        "boss": False,
    },
    "turret": {
        "name": "Wall Turret",
        "size": (40, 40),
        "max_hp": 84,
        "speed": 0,
        "damage": 12,
        "xp": 30,
        "color": (96, 184, 255),
        "secondary": (35, 54, 79),
        "aggro": 620,
        "fire_delay": 1.45,
        "boss": False,
    },
    "riot_guard": {
        "name": "Riot Guard",
        "size": (52, 62),
        "max_hp": 148,
        "speed": 92,
        "damage": 18,
        "xp": 46,
        "color": (156, 154, 170),
        "secondary": (94, 86, 102),
        "aggro": 320,
        "fire_delay": 99.0,
        "boss": False,
    },
    "shock_engineer": {
        "name": "Shock Engineer",
        "size": (42, 58),
        "max_hp": 98,
        "speed": 106,
        "damage": 13,
        "xp": 42,
        "color": (110, 228, 255),
        "secondary": (32, 63, 78),
        "aggro": 560,
        "fire_delay": 1.55,
        "boss": False,
    },
    "crawler_drone": {
        "name": "Crawler Drone",
        "size": (38, 28),
        "max_hp": 54,
        "speed": 238,
        "damage": 12,
        "xp": 24,
        "color": (172, 198, 187),
        "secondary": (255, 116, 116),
        "aggro": 320,
        "fire_delay": 99.0,
        "boss": False,
    },
    "flame_hound": {
        "name": "Flame Hound",
        "size": (48, 40),
        "max_hp": 92,
        "speed": 228,
        "damage": 19,
        "xp": 34,
        "color": (240, 136, 79),
        "secondary": (110, 42, 28),
        "aggro": 330,
        "fire_delay": 99.0,
        "boss": False,
    },
    "thorn_warden": {
        "name": "Thorn Warden",
        "size": (88, 108),
        "max_hp": 720,
        "speed": 150,
        "damage": 24,
        "xp": 220,
        "color": (168, 112, 255),
        "secondary": (50, 34, 84),
        "aggro": 800,
        "fire_delay": 1.1,
        "boss": True,
    },
    "lord_malgrin": {
        "name": "Lord Malgrin",
        "size": (94, 118),
        "max_hp": 980,
        "speed": 162,
        "damage": 28,
        "xp": 300,
        "color": (255, 112, 112),
        "secondary": (114, 42, 42),
        "aggro": 900,
        "fire_delay": 0.88,
        "boss": True,
    },
}

ENEMY_TAUNTS = {
    "guard": [
        "Hold the line!",
        "The princess stays here!",
        "You're not clearing this base.",
    ],
    "gunner": [
        "Target locked.",
        "No hero crosses my lane.",
        "Say hello to the prison yard.",
    ],
    "hound": [
        "Run, little breaker!",
        "I smell fear.",
        "Fresh blood on the floor.",
    ],
    "turret": [
        "Eliminate intruder.",
        "Base security engaged.",
        "No escape vector found.",
    ],
    "riot_guard": [
        "Your shots stop at the shield wall.",
        "This corridor does not break.",
        "Come closer if you want through.",
    ],
    "shock_engineer": [
        "I'll wire your armor shut.",
        "Voltage rising.",
        "Stand still for calibration.",
    ],
    "crawler_drone": [
        "Skitter. Cut. Repeat.",
        "Target ankles first.",
        "Maintenance mode: maul intruder.",
    ],
    "flame_hound": [
        "Run hotter, burn faster.",
        "The forge wants fresh prey.",
        "I chase sparks and bone.",
    ],
    "thorn_warden": [
        "Kneel in the ivy and rust.",
        "You reached the first gate and nothing more.",
    ],
    "lord_malgrin": [
        "You will watch the princess remain mine.",
        "Every floor you climbed ends here.",
    ],
}

WORLD_THEMES = {
    1: {
        "world_name": "World 1: Grimwood Perimeter",
        "sky": (18, 24, 33),
        "mid": (34, 50, 57),
        "accent": (93, 199, 255),
        "platform": (76, 102, 108),
        "trim": (116, 143, 150),
    },
    2: {
        "world_name": "World 2: Prison Forge Citadel",
        "sky": (27, 20, 23),
        "mid": (62, 42, 43),
        "accent": (255, 148, 94),
        "platform": (116, 86, 80),
        "trim": (171, 128, 108),
    },
}

GROUND = (0, 648, WIDTH, 72)

LEVELS = [
    {
        "world": 1,
        "level": 1,
        "name": "Fallen Gate",
        "goal": "Find the first route into the perimeter prison chain.",
        "spawn": (80, 590),
        "platforms": [
            GROUND,
            (154, 540, 220, 18),
            (468, 450, 220, 18),
            (824, 360, 210, 18),
            (1008, 540, 170, 18),
        ],
        "weapon_pickups": [weapon_pickup("iron_saber", 522, 410)],
        "item_pickups": [item_pickup("medkit", 1032, 500)],
        "enemy_spawns": [
            enemy("guard", 330, 594, "No prisoner gets past us.", (210, 430)),
            enemy("hound", 896, 608, "Fresh meat in the gate!", (842, 1130)),
            enemy("gunner", 528, 394, "The princess is not your mission anymore.", (470, 640)),
        ],
        "intro": [
            "Princess Elara was moved through the outer perimeter two nights ago.",
            "Break through the gate, gear up, and climb toward the base.",
        ],
    },
    {
        "world": 1,
        "level": 2,
        "name": "Broken Aqueduct",
        "goal": "Cross the ruined water channel without getting pinned down.",
        "spawn": (72, 590),
        "platforms": [
            GROUND,
            (92, 538, 200, 18),
            (344, 470, 204, 18),
            (620, 530, 214, 18),
            (890, 438, 230, 18),
        ],
        "weapon_pickups": [weapon_pickup("burst_rifle", 988, 398)],
        "item_pickups": [item_pickup("alloy_scrap", 412, 430), item_pickup("medkit", 702, 490)],
        "enemy_spawns": [
            enemy("guard", 160, 484, "No one reaches the upper locks.", (90, 274)),
            enemy("gunner", 430, 414, "Take the shot before they jump.", (350, 548)),
            enemy("hound", 740, 490, "Bite first, drag later.", (620, 834)),
            enemy("turret", 1040, 398, "Acquiring target.", None),
        ],
        "intro": ["The aqueduct is wrecked, but the perimeter guards are still using it as a kill lane."],
    },
    {
        "world": 1,
        "level": 3,
        "name": "Prison Yard",
        "goal": "Push through the holding cells and collect evidence of the transfer.",
        "spawn": (86, 590),
        "platforms": [
            GROUND,
            (140, 538, 200, 18),
            (396, 462, 200, 18),
            (660, 382, 180, 18),
            (924, 462, 230, 18),
        ],
        "weapon_pickups": [],
        "item_pickups": [item_pickup("prison_key", 724, 342), item_pickup("medkit", 972, 422)],
        "enemy_spawns": [
            enemy("hound", 212, 608, "The cells are locked for a reason.", (144, 340)),
            enemy("guard", 448, 416, "You don't belong in the yard.", (400, 590)),
            enemy("gunner", 718, 336, "Prison transfer is already complete.", (664, 822)),
            enemy("guard", 1038, 416, "Turn back while you still can.", (934, 1138)),
        ],
        "intro": ["The yard still carries transport records. If the princess came through here, someone logged it."],
    },
    {
        "world": 1,
        "level": 4,
        "name": "Radar Walk",
        "goal": "Disable the watch platforms guarding the first boss gate.",
        "spawn": (70, 590),
        "platforms": [
            GROUND,
            (88, 454, 200, 18),
            (344, 358, 194, 18),
            (632, 454, 194, 18),
            (920, 326, 212, 18),
        ],
        "weapon_pickups": [weapon_pickup("scattergun", 690, 414)],
        "item_pickups": [item_pickup("alloy_scrap", 388, 318)],
        "enemy_spawns": [
            enemy("turret", 160, 414, "Radar sweep live.", None),
            enemy("gunner", 398, 310, "This lane belongs to us.", (350, 518)),
            enemy("hound", 700, 568, "I'll drag you off the catwalk.", (632, 840)),
            enemy("guard", 980, 278, "No one crosses into the throne root.", (924, 1120)),
        ],
        "intro": ["One more floor. The first warden is holding the elevator into the inner route."],
    },
    {
        "world": 1,
        "level": 5,
        "name": "Thorn Warden",
        "goal": "Defeat the first boss and open the route to the Blackfang Base.",
        "spawn": (110, 590),
        "platforms": [
            GROUND,
            (188, 512, 232, 18),
            (864, 512, 232, 18),
            (474, 400, 320, 18),
        ],
        "weapon_pickups": [],
        "item_pickups": [item_pickup("medkit", 580, 360)],
        "enemy_spawns": [
            enemy("thorn_warden", 576, 284, "You made noise in my garden. Now bleed for it.", (220, 1020), "Thorn Warden"),
        ],
        "intro": ["Boss floor. Break the Thorn Warden and the first world opens beneath you."],
    },
    {
        "world": 2,
        "level": 6,
        "name": "Cargo Lift",
        "goal": "Enter Blackfang Base and find the prisoner transit route.",
        "spawn": (90, 590),
        "platforms": [
            GROUND,
            (130, 520, 200, 18),
            (402, 430, 208, 18),
            (722, 520, 190, 18),
            (990, 410, 188, 18),
        ],
        "weapon_pickups": [weapon_pickup("royal_blade", 1038, 370)],
        "item_pickups": [item_pickup("royal_seal", 450, 390), item_pickup("medkit", 762, 480)],
        "enemy_spawns": [
            enemy("riot_guard", 184, 466, "Shield wall up. No one rides this lift.", (130, 320)),
            enemy("shock_engineer", 458, 382, "Cargo sparks are lethal today.", (402, 590)),
            enemy("turret", 766, 480, "Dock lockdown active.", None),
            enemy("crawler_drone", 1060, 612, "The lower rails chew intruders first.", (950, 1170)),
        ],
        "intro": [
            "The first boss lock broke. You are inside Blackfang Base.",
            "Princess Elara is somewhere above the core prison deck. Keep climbing.",
        ],
    },
    {
        "world": 2,
        "level": 7,
        "name": "Furnace Spine",
        "goal": "Climb the furnace stacks without letting the gunners trap you.",
        "spawn": (84, 590),
        "platforms": [
            GROUND,
            (110, 566, 170, 18),
            (332, 474, 190, 18),
            (590, 378, 194, 18),
            (872, 474, 208, 18),
            (1072, 330, 140, 18),
        ],
        "weapon_pickups": [],
        "item_pickups": [item_pickup("alloy_scrap", 626, 338), item_pickup("medkit", 1104, 290)],
        "enemy_spawns": [
            enemy("flame_hound", 140, 526, "The forge breathes through me.", (110, 280)),
            enemy("riot_guard", 382, 418, "Heat or steel, you stop here.", (332, 516)),
            enemy("shock_engineer", 640, 330, "Perfect angle for a short circuit.", (590, 774)),
            enemy("crawler_drone", 932, 602, "Crawler line active.", (872, 1080)),
            enemy("turret", 1094, 290, "Heatlock engaged.", None),
        ],
        "intro": ["The furnace spine feeds power toward the prison deck. Break through and keep the pressure on."],
    },
    {
        "world": 2,
        "level": 8,
        "name": "Lab Barracks",
        "goal": "Sweep the research wing and locate the command route.",
        "spawn": (76, 590),
        "platforms": [
            GROUND,
            (146, 438, 214, 18),
            (456, 350, 214, 18),
            (768, 438, 194, 18),
            (1012, 540, 184, 18),
        ],
        "weapon_pickups": [weapon_pickup("plasma_carbine", 514, 310)],
        "item_pickups": [item_pickup("alloy_scrap", 826, 398), item_pickup("medkit", 1050, 500)],
        "enemy_spawns": [
            enemy("crawler_drone", 210, 610, "Lab cleanup protocol: shred intruder.", (146, 360)),
            enemy("shock_engineer", 514, 302, "Test the new weapons on them.", (456, 658)),
            enemy("turret", 824, 398, "Lab corridor secure.", None),
            enemy("riot_guard", 1030, 478, "Specimens do not pass the blast door.", (1008, 1196)),
        ],
        "intro": ["The lab barracks lead straight to the command hall. Take what gear you can find and move."],
    },
    {
        "world": 2,
        "level": 9,
        "name": "Throne Approach",
        "goal": "Reach the core prison doors and prepare for the final boss.",
        "spawn": (86, 590),
        "platforms": [
            GROUND,
            (112, 522, 210, 18),
            (406, 430, 200, 18),
            (688, 340, 204, 18),
            (972, 430, 198, 18),
        ],
        "weapon_pickups": [weapon_pickup("plasma_raygun", 770, 300)],
        "item_pickups": [item_pickup("medkit", 456, 390), item_pickup("royal_seal", 736, 300)],
        "enemy_spawns": [
            enemy("shock_engineer", 164, 474, "Last hall before the prison.", (112, 304)),
            enemy("flame_hound", 458, 388, "I can smell the throne room.", (406, 606)),
            enemy("riot_guard", 740, 284, "Lord Malgrin stands behind me.", (688, 892)),
            enemy("turret", 1032, 390, "Prison door targeting live.", None),
        ],
        "intro": [
            "The throne approach is the last corridor. Princess Elara is somewhere beyond the core doors.",
            "Blackfang left an experimental plasma raygun on the upper platform. Take it before the prison fight.",
        ],
    },
    {
        "world": 2,
        "level": 10,
        "name": "Core Prison",
        "goal": "Defeat Lord Malgrin and uncover where Princess Elara was taken.",
        "spawn": (90, 590),
        "platforms": [
            GROUND,
            (190, 520, 214, 18),
            (876, 520, 214, 18),
            (474, 390, 332, 18),
        ],
        "weapon_pickups": [],
        "item_pickups": [item_pickup("medkit", 590, 350)],
        "enemy_spawns": [
            enemy("lord_malgrin", 570, 272, "The princess is my bargaining chip. Come earn her.", (220, 1040), "Lord Malgrin"),
        ],
        "intro": [
            "Final floor. Princess Elara is held in the core prison above the fight.",
            "Break Malgrin, reach the cage, and find out if you are already too late.",
        ],
        "princess_pos": (1080, 182),
    },
]

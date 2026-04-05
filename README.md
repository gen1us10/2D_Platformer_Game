# 2D Platformer Game & pygame_physics

2D platformer game created in Python using Pygame, developed as part of a bachelor thesis project. The game demonstrates physical properties such as gravity, collisions, elastic bounce, surface friction and weight effects across five levels.

The project also includes **pygame_physics** — a reusable Python package that contains the core physics functions used in the game.

---

## Running the game

### Option 1 — Executable (Windows)
Download and run `dist/2D_Platformer.exe`. No Python or dependencies required.

### Option 2 — From source
```bash
pip install .
python main.py
```

---

## Controls

| Key | Action |
|-----|--------|
| `← / A` | Move left |
| `→ / D` | Move right |
| `Space / W / ↑` | Jump |
| `E` | Enter door / Pick up / Drop box |
| `F` | Aim and throw apple (Level 5) |
| `R` | Restart level |
| `Esc` | Return to menu |

---

## Levels

**Level 1 — Gravity and basic movement**
Move across platforms, find the key and reach the door to finish the level.

**Level 2 — Collisions with obstacles (AABB)**
After spawning, enter the door on the left — it leads to a second scene where the key is located. Watch out for spikes and rotating saws. Return through the door and reach the final door to finish.

**Level 3 — Elastic bounce**
Same two-scene structure as Level 2. The entire floor is covered with spikes, so you must use the springs to move between platforms. Find the key in the second scene and return.

**Level 4 — Surface friction**
Two scenes again. The level introduces ice platforms — the player slides and stops slowly on ice compared to normal surfaces. Push boxes to use them as stepping stones to reach higher platforms.

**Level 5 — Weight and object manipulation**
Single scene. Pick up boxes with `E` and collect apples — carrying them slows you down. Throw apples with `F` to break the chain holding the key. After two hits the chain breaks, the key falls and you can pick it up. Bring the key to the door on the left.

---

## Installation

### From GitHub
```bash
pip install git+https://github.com/gen1us10/2D_Platformer_Game
```

### Locally (from project folder)
```bash
pip install .
```

## Features

- **AABB collision detection** — axis-aligned bounding box collision resolution
- **Player physics** — gravity, friction, jump with coyote time and jump buffer
- **Platform** — surface with configurable friction and restitution (bounciness)
- **Helper functions** — `apply_friction`, `center_distance`

## Quick Start

```python
import pygame
from pygame_physics import Player, Platform, step_player, GRAVITY

pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock  = pygame.time.Clock()

platforms = [
    Platform(pygame.Rect(0, 640, 1280, 80), friction=12.0, kind="normal"),
]
player = Player(rect=pygame.Rect(100, 560, 40, 60))

while True:
    dt = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.request_jump()

    player.handle_input(pygame.key.get_pressed())
    step_player(player, platforms, dt)

    screen.fill((30, 30, 30))
    pygame.draw.rect(screen, (100, 200, 100), player.rect)
    for p in platforms:
        pygame.draw.rect(screen, (150, 100, 50), p.rect)
    pygame.display.flip()
```

## Package reference

### Classes

#### `Player`
| Attribute | Type | Description |
|-----------|------|-------------|
| `rect` | `pygame.Rect` | Collision rectangle |
| `vx`, `vy` | `float` | Velocity in px/s |
| `on_ground` | `bool` | True if standing on a surface |
| `facing_right` | `bool` | Direction the player faces |
| `COYOTE_TIME` | `float` | Jump grace period after leaving platform (default 0.10 s) |
| `JUMP_BUFFER_TIME` | `float` | Jump input memory before landing (default 0.10 s) |

| Method | Description |
|--------|-------------|
| `handle_input(keys, dt, on_ice, move_speed)` | Read keyboard and update velocity |
| `request_jump()` | Register a jump input |
| `update_jump(dt, jump_speed)` | Process coyote time and jump buffer |
| `apply_gravity(dt, gravity)` | Apply gravitational acceleration |

#### `Platform`
| Attribute | Type | Description |
|-----------|------|-------------|
| `rect` | `pygame.Rect` | Bounding rectangle |
| `friction` | `float` | Friction coefficient (0.0 = ice, 12.0 = normal) |
| `restitution` | `float` | Bounciness (0.0 = no bounce) |
| `kind` | `str` | Surface type: `"normal"`, `"ice"`, `"wall"`, `"crate"` |

### Functions

| Function | Description |
|----------|-------------|
| `resolve_collisions_axis(entity, platforms, axis)` | AABB collision resolution for one axis |
| `apply_friction(entity, dt, friction)` | Apply friction to horizontal movement |
| `center_distance(r1, r2)` | Distance between centres of two rects |
| `step_player(player, platforms, dt, ...)` | Full physics step for the player |

### Constants

| Constant | Default | Description |
|----------|---------|-------------|
| `GRAVITY` | 1800.0 | Gravitational acceleration (px/s²) |
| `MOVE_SPEED` | 480.0 | Default horizontal speed (px/s) |
| `JUMP_SPEED` | 780.0 | Default jump velocity (px/s) |
| `FRICTION_NORMAL` | 12.0 | Normal surface friction coefficient |
| `ACCEL_ICE` | 700.0 | Acceleration on ice (px/s²) |
| `DECEL_ICE` | 300.0 | Deceleration on ice (px/s²) |

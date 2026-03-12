import pygame
from dataclasses import dataclass
import math

WIDTH, HEIGHT = 1280, 720
FPS = 60

ASSET_PLAYER        = "assets/player.png"
ASSET_BG            = "assets/bg.png"
ASSET_PLATFORM      = "assets/platform.png"
ASSET_CRATE         = "assets/main_crate.png"
ASSET_CRATE_BROKEN  = "assets/crate.png"

GRAVITY         = 1800.0
MOVE_SPEED      = 480.0
JUMP_SPEED      = 780.0
FRICTION_NORMAL = 12.0

CARRY_SPEED_MULT = 0.55
CARRY_JUMP_MULT  = 0.65

PICKUP_DIST = 70
FLOOR_Y     = HEIGHT - 80
CAM_THRESHOLD = WIDTH // 2
WORLD_W     = 3200
BOX_SIZE    = 60
FALL_VY     = 400.0

PLAT1_H = 60
PLAT2_H = 200
PLAT3_H = 380


@dataclass
class Platform:
    rect: pygame.Rect
    friction: float
    kind: str


@dataclass
class Player:
    rect: pygame.Rect
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    facing_right: bool = True
    coyote_timer: float = 0.0
    jump_buffer: float = 0.0
    carrying: bool = False

    COYOTE_TIME      = 0.10
    JUMP_BUFFER_TIME = 0.10

    def eff_speed(self):
        return MOVE_SPEED * CARRY_SPEED_MULT if self.carrying else MOVE_SPEED

    def eff_jump(self):
        return JUMP_SPEED * CARRY_JUMP_MULT if self.carrying else JUMP_SPEED

    def handle_input(self, keys, dt):
        left  = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        if left:
            self.vx = -self.eff_speed()
            self.facing_right = False
        elif right:
            self.vx = self.eff_speed()
            self.facing_right = True
        else:
            self.vx = 0.0

    def request_jump(self):
        self.jump_buffer = self.JUMP_BUFFER_TIME

    def update_jump(self, dt):
        self.jump_buffer  = max(0.0, self.jump_buffer  - dt)
        self.coyote_timer = max(0.0, self.coyote_timer - dt)
        if self.jump_buffer > 0 and (self.on_ground or self.coyote_timer > 0):
            self.vy           = -self.eff_jump()
            self.on_ground    = False
            self.coyote_timer = 0.0
            self.jump_buffer  = 0.0


@dataclass
class CarryBox:
    rect: pygame.Rect
    spawn_x: int
    spawn_y: int
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    broken: bool = False
    dead: bool = False
    carried: bool = False
    shake_timer: float = 0.0


def load_image(path):
    return pygame.image.load(path).convert_alpha()


def crop_frame(sheet, x, y, w, h, scale=1.0):
    frame = pygame.Surface((w, h), pygame.SRCALPHA)
    frame.blit(sheet, (0, 0), pygame.Rect(x, y, w, h))
    if scale != 1.0:
        frame = pygame.transform.scale(frame, (int(w * scale), int(h * scale)))
    return frame


def crop_image(img, x, y, w, h):
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.blit(img, (0, 0), pygame.Rect(x, y, w, h))
    return out


def draw_tiled(surface, tile, area, cam_x=0, cam_y=0):
    tw, th = tile.get_size()
    draw_rect = pygame.Rect(area.x - cam_x, area.y - cam_y, area.width, area.height)
    prev_clip = surface.get_clip()
    surface.set_clip(draw_rect)
    for yy in range(draw_rect.top, draw_rect.bottom, th):
        for xx in range(draw_rect.left, draw_rect.right, tw):
            surface.blit(tile, (xx, yy))
    surface.set_clip(prev_clip)


def resolve_collisions_axis(player, platforms, axis):
    for p in platforms:
        if not player.rect.colliderect(p.rect):
            continue
        if axis == "x":
            if player.vx > 0:
                player.rect.right = p.rect.left
            elif player.vx < 0:
                player.rect.left = p.rect.right
            player.vx = 0
        else:
            if player.vy > 0:
                player.rect.bottom = p.rect.top
                player.on_ground = True
            elif player.vy < 0:
                player.rect.top = p.rect.bottom
            player.vy = 0


def get_ground_platform(player, platforms):
    check = pygame.Rect(player.rect.x, player.rect.bottom, player.rect.width, 2)
    for p in platforms:
        if p.kind == "wall":
            continue
        if check.colliderect(p.rect):
            return p
    return None


def apply_friction(player, dt, friction):
    if player.on_ground:
        player.vx *= max(0.0, 1.0 - friction * dt)


def center_distance(r1, r2):
    dx = r1.centerx - r2.centerx
    dy = r1.centery - r2.centery
    return math.sqrt(dx * dx + dy * dy)


def build_platforms():
    F = FLOOR_Y
    return [
        Platform(pygame.Rect(0,       F,      WORLD_W,         80), FRICTION_NORMAL, "normal"),
        Platform(pygame.Rect(-20,  -1000,      20, HEIGHT + 1000), FRICTION_NORMAL, "wall"),
        Platform(pygame.Rect(WORLD_W, -1000,   20, HEIGHT + 1000), FRICTION_NORMAL, "wall"),
        Platform(pygame.Rect(500,  F - PLAT1_H, 700, 22), FRICTION_NORMAL, "normal"),
        Platform(pygame.Rect(1380, F - PLAT2_H, 480, 22), FRICTION_NORMAL, "normal"),
        Platform(pygame.Rect(2100, F - PLAT3_H, 560, 22), FRICTION_NORMAL, "normal"),
    ]


def build_boxes():
    F = FLOOR_Y
    return [
        CarryBox(
            rect    = pygame.Rect(300, F - BOX_SIZE, BOX_SIZE, BOX_SIZE),
            spawn_x = 300,
            spawn_y = F - BOX_SIZE,
        ),
        CarryBox(
            rect    = pygame.Rect(1450, F - PLAT2_H - BOX_SIZE, BOX_SIZE, BOX_SIZE),
            spawn_x = 1450,
            spawn_y = F - PLAT2_H - BOX_SIZE,
        ),
    ]


def update_box_physics(b, platforms, dt):
    if b.carried or b.dead:
        return

    b.vy += GRAVITY * dt

    b.rect.x += int(b.vx * dt)
    for p in platforms:
        if p.kind == "wall" or not b.rect.colliderect(p.rect):
            continue
        if b.vx > 0:
            b.rect.right = p.rect.left
        elif b.vx < 0:
            b.rect.left = p.rect.right
        b.vx = 0.0

    fall_vy     = b.vy
    b.on_ground = False
    b.rect.y   += int(b.vy * dt)
    landed_p    = None
    for p in platforms:
        if p.kind == "wall" or not b.rect.colliderect(p.rect):
            continue
        if b.vy > 0:
            b.rect.bottom = p.rect.top
            b.on_ground   = True
            b.vy          = 0
            landed_p      = p
        elif b.vy < 0:
            b.rect.top = p.rect.bottom
            b.vy       = 0

    if landed_p and fall_vy >= FALL_VY:
        if b.broken:
            b.dead = True
        else:
            b.broken      = True
            b.shake_timer = 0.4

    b.shake_timer = max(0.0, b.shake_timer - dt)

    if b.on_ground:
        decel = 800.0
        if b.vx > 0:
            b.vx = max(0.0, b.vx - decel * dt)
        elif b.vx < 0:
            b.vx = min(0.0, b.vx + decel * dt)

    if b.rect.top > FLOOR_Y + 200:
        if b.broken:
            b.dead = True
        else:
            b.broken = True
            b.rect.topleft = (b.spawn_x, b.spawn_y)
            b.vx = b.vy = 0.0


def attach_carried_box(b, player):
    gap = 3
    if player.facing_right:
        b.rect.left = player.rect.right + gap
    else:
        b.rect.right = player.rect.left - gap
    b.rect.bottom = player.rect.bottom
    b.vx = b.vy = 0.0


def resolve_player_box_collision(player, b):
    if b.dead or b.carried or not player.rect.colliderect(b.rect):
        return
    olx = player.rect.right  - b.rect.left
    orx = b.rect.right - player.rect.left
    oty = player.rect.bottom - b.rect.top
    oby = b.rect.bottom - player.rect.top
    mx, my = min(olx, orx), min(oty, oby)
    if my < mx:
        if oty < oby and player.vy >= 0:
            player.rect.bottom = b.rect.top
            player.on_ground   = True
            player.vy          = 0
        elif oby < oty and player.vy < 0:
            player.rect.top = b.rect.bottom
            player.vy       = 0
    else:
        if olx < orx and player.vx > 0:
            player.rect.right = b.rect.left
            player.vx         = 0.0
        elif orx < olx and player.vx < 0:
            player.rect.left = b.rect.right
            player.vx        = 0.0


def main():
    pygame.init()
    screen   = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Level 5")
    clock    = pygame.time.Clock()
    font     = pygame.font.SysFont("Arial", 20)
    font_big = pygame.font.SysFont("Arial", 36, bold=True)

    bg_scaled = pygame.transform.scale(load_image(ASSET_BG), (WIDTH, HEIGHT))

    platform_img = load_image(ASSET_PLATFORM)
    strip      = crop_image(platform_img, 0, 16, platform_img.get_width(), 64)
    tile_floor = pygame.transform.smoothscale(strip, (256, 80))
    tile_thin  = pygame.transform.smoothscale(strip, (256, 22))

    crate_img    = pygame.transform.smoothscale(load_image(ASSET_CRATE),        (BOX_SIZE, BOX_SIZE))
    crate_broken = pygame.transform.smoothscale(load_image(ASSET_CRATE_BROKEN), (BOX_SIZE, BOX_SIZE))

    FRAME_W, FRAME_H = 64, 64
    SCALE = 1.8
    sheet      = load_image(ASSET_PLAYER)
    img_idle   = crop_frame(sheet, 0, 0 * FRAME_H, FRAME_W, FRAME_H, SCALE)
    walk_left  = [crop_frame(sheet, i * FRAME_W, 1 * FRAME_H, FRAME_W, FRAME_H, SCALE) for i in range(4)]
    walk_right = [crop_frame(sheet, i * FRAME_W, 2 * FRAME_H, FRAME_W, FRAME_H, SCALE) for i in range(4)]

    SPRITE_W = int(FRAME_W * SCALE)
    SPRITE_H = int(FRAME_H * SCALE)
    HB_W = int(SPRITE_W * 0.52)
    HB_H = int(SPRITE_H * 0.78)
    SP_OX = -(SPRITE_W - HB_W) // 2
    SP_OY = -(SPRITE_H - HB_H)

    F         = FLOOR_Y
    platforms = build_platforms()
    boxes     = build_boxes()
    player    = Player(rect=pygame.Rect(120, F - HB_H, HB_W, HB_H))
    carried   = None
    goal_rect = pygame.Rect(2550, F - PLAT3_H - 22, 80, 22)

    state = {
        "cam_x":       0.0,
        "cam_y":       0.0,
        "won":         False,
        "win_timer":   0.0,
        "anim_timer":  0.0,
        "anim_frame":  0,
        "fade_alpha":  0.0,
        "fade_state":  None,
        "fade_target": None,
    }

    def reset():
        nonlocal boxes, carried
        player.rect.topleft = (120, F - HB_H)
        player.vx = player.vy = 0.0
        player.on_ground = False
        player.carrying  = False
        carried          = None
        boxes            = build_boxes()
        state.update({
            "cam_x": 0.0, "cam_y": 0.0,
            "won": False, "win_timer": 0.0,
            "anim_timer": 0.0, "anim_frame": 0,
            "fade_alpha": 0.0, "fade_state": None, "fade_target": None,
        })

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reset()
                if event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                    player.request_jump()
                if event.key == pygame.K_e:
                    if player.carrying and carried:
                        carried.carried = False
                        carried.vx      = 160.0 if player.facing_right else -160.0
                        carried.vy      = -60.0
                        carried         = None
                        player.carrying = False
                    else:
                        for b in boxes:
                            if b.dead or b.carried:
                                continue
                            if center_distance(player.rect, b.rect) < PICKUP_DIST:
                                b.carried       = True
                                carried         = b
                                player.carrying = True
                                break

        if state["fade_state"] == "out":
            state["fade_alpha"] = min(1.0, state["fade_alpha"] + dt * 10.0)
            if state["fade_alpha"] >= 1.0:
                reset()
                state["fade_state"] = "in"
        elif state["fade_state"] == "in":
            state["fade_alpha"] = max(0.0, state["fade_alpha"] - dt * 3.0)
            if state["fade_alpha"] <= 0.0:
                state["fade_state"]  = None
                state["fade_target"] = None

        if state["fade_state"] != "out":
            player.handle_input(pygame.key.get_pressed(), dt)

        player.vy += GRAVITY * dt
        player.rect.x += int(player.vx * dt)
        resolve_collisions_axis(player, platforms, "x")

        was_on_ground    = player.on_ground
        player.on_ground = False
        player.rect.y   += int(player.vy * dt)
        resolve_collisions_axis(player, platforms, "y")

        for b in boxes:
            if b.dead or b.carried:
                continue
            p_bot  = pygame.Rect(player.rect.x, player.rect.bottom - 2, player.rect.width, 4)
            bx_top = pygame.Rect(b.rect.x,      b.rect.top - 2,         b.rect.width,      4)
            if p_bot.colliderect(bx_top) and player.vy >= 0:
                player.rect.bottom = b.rect.top
                player.on_ground   = True
                player.vy          = 0

        if was_on_ground and not player.on_ground:
            player.coyote_timer = player.COYOTE_TIME

        player.update_jump(dt)

        ground_plat = get_ground_platform(player, platforms)
        if player.on_ground and ground_plat:
            apply_friction(player, dt, ground_plat.friction)

        if player.carrying and carried:
            attach_carried_box(carried, player)

        for b in boxes:
            update_box_physics(b, platforms, dt)
            if b.dead and state["fade_state"] is None:
                state["fade_state"]  = "out"
                state["fade_target"] = "death"

        for b in boxes:
            if not player.carrying:
                resolve_player_box_collision(player, b)

        if not state["won"] and player.rect.colliderect(goal_rect):
            state["won"] = True

        if state["won"]:
            state["win_timer"] += dt

        if player.rect.top > F + 80 and state["fade_state"] is None:
            state["fade_state"]  = "out"
            state["fade_target"] = "death"

        target_x = player.rect.centerx - CAM_THRESHOLD
        target_x = max(0, min(target_x, WORLD_W - WIDTH))
        state["cam_x"] += (target_x - state["cam_x"]) * min(1.0, 8.0 * dt)

        target_y = player.rect.centery - HEIGHT // 2
        target_y = max(-HEIGHT, min(target_y, 0))
        state["cam_y"] += (target_y - state["cam_y"]) * min(1.0, 8.0 * dt)

        cx = int(state["cam_x"])
        cy = int(state["cam_y"])

        bg_offset = int(cx * 0.4) % WIDTH
        screen.blit(bg_scaled, (-bg_offset, 0))
        screen.blit(bg_scaled, (WIDTH - bg_offset, 0))

        for p in platforms:
            if p.kind == "wall":
                continue
            tile = tile_floor if p.rect.height >= 60 else tile_thin
            draw_tiled(screen, tile, p.rect, cam_x=cx, cam_y=cy)
            pygame.draw.rect(screen, (80, 40, 10),
                pygame.Rect(p.rect.x - cx, p.rect.y - cy, p.rect.width, p.rect.height), 2)

        for b in boxes:
            if b.dead:
                ghost = crate_broken.copy()
                ghost.set_alpha(35)
                screen.blit(ghost, (b.spawn_x - cx, b.spawn_y - cy))
                continue
            img   = crate_broken if b.broken else crate_img
            shake = int(math.sin(b.shake_timer * 35) * 3) if b.shake_timer > 0 else 0
            bx_d  = b.rect.x - cx + shake
            by_d  = b.rect.y - cy
            if b.carried:
                gl = pygame.Surface((BOX_SIZE + 12, BOX_SIZE + 12), pygame.SRCALPHA)
                gl.fill((255, 240, 80, 50))
                screen.blit(gl, (bx_d - 6, by_d - 6))
            screen.blit(img, (bx_d, by_d))

        moving = abs(player.vx) > 5
        if moving:
            state["anim_timer"] += dt
            if state["anim_timer"] >= 1.0 / 8:
                state["anim_timer"] -= 1.0 / 8
                state["anim_frame"] = (state["anim_frame"] + 1) % 4
        else:
            state["anim_timer"] = 0.0
            state["anim_frame"] = 0

        sprite = (walk_right[state["anim_frame"]] if player.vx > 5 else
                  walk_left [state["anim_frame"]] if player.vx < -5 else img_idle)
        screen.blit(sprite, (player.rect.x - cx + SP_OX, player.rect.y + SP_OY - cy))

        ui_bg = pygame.Surface((300, 60), pygame.SRCALPHA)
        ui_bg.fill((0, 0, 0, 120))
        screen.blit(ui_bg, (10, 10))

        spd_pct  = int(player.eff_speed() / MOVE_SPEED * 100)
        jump_pct = int(player.eff_jump()  / JUMP_SPEED  * 100)
        col_carry = (255, 200, 50) if player.carrying else (200, 200, 200)
        screen.blit(font.render(
            f"Nesie debnu: {'ÁNO' if player.carrying else 'NIE'}",
            True, col_carry), (18, 15))
        screen.blit(font.render(
            f"Rýchlosť: {spd_pct}%   Skok: {jump_pct}%",
            True, (200, 200, 255)), (18, 38))

        hint_bg = pygame.Surface((400, 28), pygame.SRCALPHA)
        hint_bg.fill((0, 0, 0, 100))
        screen.blit(hint_bg, (10, HEIGHT - 38))
        screen.blit(font.render(
            "← → pohyb  |  SPACE skok  |  E zdvihnúť/položiť  |  R reštart",
            True, (220, 220, 220)), (16, HEIGHT - 34))

        if state["fade_state"] is not None:
            ov = pygame.Surface((WIDTH, HEIGHT))
            ov.fill((0, 0, 0))
            ov.set_alpha(int(255 * state["fade_alpha"]))
            screen.blit(ov, (0, 0))

        if state["won"]:
            a   = min(1.0, state["win_timer"] / 0.5)
            ov2 = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov2.fill((0, 0, 0, int(120 * a)))
            screen.blit(ov2, (0, 0))
            msg = font_big.render("Úroveň dokončená! Stlač R pre reštart.",
                                  True, (255, 255, 100))
            screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        pygame.display.flip()


if __name__ == "__main__":
    main()
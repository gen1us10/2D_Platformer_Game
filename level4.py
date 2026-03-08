import pygame
from dataclasses import dataclass
import math

WIDTH, HEIGHT = 1280, 720
FPS = 60

ASSET_PLAYER        = "assets/player.png"
ASSET_BG            = "assets/bg.png"
ASSET_PLATFORM      = "assets/platform.png"
ASSET_PLATFORM_ICE  = "assets/Plateform4_Center.png"
ASSET_KEY           = "assets/key.png"
ASSET_DOOR_CLOSED   = "assets/door_closed.png"
ASSET_DOOR_OPEN     = "assets/door_open.png"
ASSET_CRATE         = "assets/crate.png"
ASSET_SAW           = "assets/saw.png"
ASSET_SPIKE         = "assets/spike.png"

GRAVITY         = 1800.0
MOVE_SPEED      = 480.0
JUMP_SPEED      = 780.0
FRICTION_NORMAL = 12.0
ACCEL_ICE       = 900.0
DECEL_ICE       = 300.0

PICKUP_DISTANCE = 50
DOOR_DISTANCE   = 70
FLOOR_Y         = HEIGHT - 80
CAM_THRESHOLD   = WIDTH // 2
SAW_RADIUS      = 22

MAIN_WORLD_W = 1400
KEY_WORLD_W  = 3600


@dataclass
class Platform:
    rect: pygame.Rect
    friction: float
    restitution: float
    kind: str


@dataclass
class Hazard:
    x: float
    y: float
    kind: str
    angle: float = 0.0


@dataclass
class Player:
    rect: pygame.Rect
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    has_key: bool = False
    facing_right: bool = True
    coyote_timer: float = 0.0
    jump_buffer: float = 0.0

    COYOTE_TIME      = 0.10
    JUMP_BUFFER_TIME = 0.10

    def handle_input(self, keys, dt, on_ice):
        left  = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        if on_ice:
            if left:
                self.vx = max(-MOVE_SPEED, self.vx - ACCEL_ICE * dt)
                self.facing_right = False
            elif right:
                self.vx = min(MOVE_SPEED, self.vx + ACCEL_ICE * dt)
                self.facing_right = True
            else:
                if self.vx > 0:
                    self.vx = max(0.0, self.vx - DECEL_ICE * dt)
                elif self.vx < 0:
                    self.vx = min(0.0, self.vx + DECEL_ICE * dt)
        else:
            if left:
                self.vx = -MOVE_SPEED
                self.facing_right = False
            elif right:
                self.vx = MOVE_SPEED
                self.facing_right = True
            else:
                self.vx = 0.0

    def request_jump(self):
        self.jump_buffer = self.JUMP_BUFFER_TIME

    def update_jump(self, dt):
        self.jump_buffer  = max(0.0, self.jump_buffer  - dt)
        self.coyote_timer = max(0.0, self.coyote_timer - dt)
        if self.jump_buffer > 0 and (self.on_ground or self.coyote_timer > 0):
            self.vy           = -JUMP_SPEED
            self.on_ground    = False
            self.coyote_timer = 0.0
            self.jump_buffer  = 0.0


@dataclass
class Key:
    rect: pygame.Rect
    collected: bool  = False
    bob_timer: float = 0.0


@dataclass
class Door:
    rect: pygame.Rect
    is_open: bool = False


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


def build_main_platforms():
    F = FLOOR_Y
    return [
        Platform(pygame.Rect(0,           F, MAIN_WORLD_W, 80), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(-20,         0, 20, HEIGHT),        FRICTION_NORMAL, 0.0, "wall"),
        Platform(pygame.Rect(MAIN_WORLD_W,0, 20, HEIGHT),        FRICTION_NORMAL, 0.0, "wall"),
    ]


def build_main_hazards():
    return []


def build_key_platforms():
    F = FLOOR_Y
    return [
        Platform(pygame.Rect(0,          F, KEY_WORLD_W, 80), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(-20,        0, 20, HEIGHT),       FRICTION_NORMAL, 0.0, "wall"),
        Platform(pygame.Rect(KEY_WORLD_W,0, 20, HEIGHT),       FRICTION_NORMAL, 0.0, "wall"),

        Platform(pygame.Rect(350,  F - 120, 200, 22), 0.0,            0.0, "ice"),
        Platform(pygame.Rect(700,  F - 200, 240, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(1050, F - 140, 200, 22), 0.0,            0.0, "ice"),
        Platform(pygame.Rect(1380, F - 220, 260, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(1750, F - 160, 220, 22), 0.0,            0.0, "ice"),
        Platform(pygame.Rect(2080, F - 240, 240, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(2430, F - 170, 200, 22), 0.0,            0.0, "ice"),
        Platform(pygame.Rect(2750, F - 250, 220, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(3080, F - 180, 200, 22), 0.0,            0.0, "ice"),
        Platform(pygame.Rect(3380, F - 260, 200, 22), FRICTION_NORMAL, 0.0, "normal"),
    ]


KEY_PLATFORM_IDX = 12


def build_key_hazards():
    return []


def main():
    pygame.init()
    screen  = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Level 4 – Povrchy s rôznym trením")
    clock   = pygame.time.Clock()
    font    = pygame.font.SysFont("Arial", 20)
    font_big = pygame.font.SysFont("Arial", 36, bold=True)

    bg_scaled = pygame.transform.scale(load_image(ASSET_BG), (WIDTH, HEIGHT))

    platform_img = load_image(ASSET_PLATFORM)
    strip      = crop_image(platform_img, 0, 16, platform_img.get_width(), 64)
    tile_floor = pygame.transform.smoothscale(strip, (256, 80))
    tile_thin  = pygame.transform.smoothscale(strip, (256, 22))

    ice_raw    = load_image(ASSET_PLATFORM_ICE)
    tile_ice   = pygame.transform.smoothscale(ice_raw, (256, 22))

    crate_img  = pygame.transform.smoothscale(load_image(ASSET_CRATE), (60, 60))
    spike_img  = pygame.transform.smoothscale(load_image(ASSET_SPIKE), (50, 50))
    saw_base   = pygame.transform.smoothscale(load_image(ASSET_SAW),   (48, 48))

    FRAME_W, FRAME_H = 64, 64
    SCALE = 1.8
    sheet = load_image(ASSET_PLAYER)
    img_idle   = crop_frame(sheet, 0, 0 * FRAME_H, FRAME_W, FRAME_H, SCALE)
    walk_left  = [crop_frame(sheet, i * FRAME_W, 1 * FRAME_H, FRAME_W, FRAME_H, SCALE) for i in range(4)]
    walk_right = [crop_frame(sheet, i * FRAME_W, 2 * FRAME_H, FRAME_W, FRAME_H, SCALE) for i in range(4)]

    SPRITE_W = int(FRAME_W * SCALE)
    SPRITE_H = int(FRAME_H * SCALE)
    HB_W = int(SPRITE_W * 0.52)
    HB_H = int(SPRITE_H * 0.78)
    SP_OX = -(SPRITE_W - HB_W) // 2
    SP_OY = -(SPRITE_H - HB_H)

    key_img = pygame.transform.smoothscale(load_image(ASSET_KEY), (48, 40))
    DOOR_W = 90
    DOOR_H = int(768 * DOOR_W / 512)
    door_img_closed = pygame.transform.smoothscale(load_image(ASSET_DOOR_CLOSED), (DOOR_W, DOOR_H))
    door_img_open   = pygame.transform.smoothscale(load_image(ASSET_DOOR_OPEN),   (DOOR_W, DOOR_H))

    main_platforms = build_main_platforms()
    main_hazards   = build_main_hazards()
    key_platforms  = build_key_platforms()
    key_hazards    = build_key_hazards()

    kp  = key_platforms[KEY_PLATFORM_IDX]
    key = Key(rect=pygame.Rect(
        kp.rect.centerx - key_img.get_width() // 2,
        kp.rect.top - key_img.get_height() - 6,
        key_img.get_width(), key_img.get_height()
    ))

    door_a = Door(rect=pygame.Rect(80, FLOOR_Y - DOOR_H, DOOR_W, DOOR_H))
    door_a.is_open = True

    door_b = Door(rect=pygame.Rect(
        MAIN_WORLD_W - DOOR_W - 60,
        FLOOR_Y - DOOR_H,
        DOOR_W, DOOR_H
    ))

    player = Player(rect=pygame.Rect(220, FLOOR_Y - HB_H, HB_W, HB_H))

    state = {
        "scene":       "main",
        "cam_x":       0.0,
        "cam_y":       0.0,
        "won":         False,
        "win_timer":   0.0,
        "anim_timer":  0.0,
        "anim_frame":  0,
        "fade_alpha":  0.0,
        "fade_state":  None,
        "fade_target": None,
        "scene_next":  None,
    }
    key_draw = key.rect.copy()

    def do_respawn():
        player.rect.topleft = (220, FLOOR_Y - HB_H)
        player.vx = player.vy = 0.0
        state["cam_x"] = 0.0
        if state["scene"] == "key_zone" and player.has_key:
            player.has_key = False
            key.collected  = False
            key.bob_timer  = 0.0

    def do_scene_switch():
        state["scene"] = state["scene_next"]
        player.rect.topleft = (220, FLOOR_Y - HB_H)
        player.vx = player.vy = 0.0
        state["cam_x"] = 0.0

    def reset():
        player.rect.topleft = (220, FLOOR_Y - HB_H)
        player.vx = player.vy = 0.0
        player.on_ground = False
        player.has_key   = False
        key.collected    = False
        key.bob_timer    = 0.0
        door_b.is_open   = False
        state.update({
            "scene": "main", "cam_x": 0.0, "cam_y": 0.0, "won": False, "win_timer": 0.0,
            "anim_timer": 0.0, "anim_frame": 0,
            "fade_alpha": 0.0, "fade_state": None,
            "fade_target": None, "scene_next": None,
        })

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        scene     = state["scene"]
        platforms = main_platforms if scene == "main" else key_platforms
        hazards   = main_hazards   if scene == "main" else key_hazards
        world_w   = MAIN_WORLD_W   if scene == "main" else KEY_WORLD_W

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
                    if state["fade_state"] is None:
                        if center_distance(player.rect, door_a.rect) < DOOR_DISTANCE:
                            state["fade_state"]  = "out"
                            state["fade_target"] = "scene"
                            state["scene_next"]  = "key_zone" if scene == "main" else "main"

        fs = state["fade_state"]
        if fs == "out":
            state["fade_alpha"] = min(1.0, state["fade_alpha"] + dt * 10.0)
            if state["fade_alpha"] >= 1.0:
                if state["fade_target"] == "death":
                    do_respawn()
                else:
                    do_scene_switch()
                state["fade_state"] = "in"
        elif fs == "in":
            state["fade_alpha"] = max(0.0, state["fade_alpha"] - dt * 3.0)
            if state["fade_alpha"] <= 0.0:
                state["fade_state"]  = None
                state["fade_target"] = None
                state["scene_next"]  = None

        if state["fade_state"] != "out":
            ground_plat = get_ground_platform(player, platforms)
            on_ice = ground_plat is not None and ground_plat.kind == "ice"
            player.handle_input(pygame.key.get_pressed(), dt, on_ice)

        player.vy += GRAVITY * dt
        player.rect.x += player.vx * dt
        resolve_collisions_axis(player, platforms, "x")

        was_on_ground    = player.on_ground
        player.on_ground = False
        player.rect.y   += player.vy * dt
        resolve_collisions_axis(player, platforms, "y")

        if was_on_ground and not player.on_ground:
            player.coyote_timer = player.COYOTE_TIME

        ground_plat = get_ground_platform(player, platforms)
        if player.on_ground and ground_plat and ground_plat.kind != "ice":
            apply_friction(player, dt, ground_plat.friction)

        player.update_jump(dt)

        for h in hazards:
            if h.kind == "saw":
                h.angle = (h.angle + 120.0 * dt) % 360.0

        if state["fade_state"] is None:
            for h in hazards:
                hit = False
                if h.kind == "spike":
                    hrect = pygame.Rect(h.x - 20, h.y - 20, 40, 40)
                    hit = player.rect.colliderect(hrect)
                elif h.kind == "saw":
                    dx = player.rect.centerx - h.x
                    dy = player.rect.centery - h.y
                    hit = math.sqrt(dx * dx + dy * dy) < SAW_RADIUS + 18
                if hit:
                    state["fade_state"]  = "out"
                    state["fade_target"] = "death"
                    break

        if scene == "key_zone" and not key.collected:
            key.bob_timer += dt
            bob_y    = int(math.sin(key.bob_timer * 3.0) * 5)
            key_draw = pygame.Rect(key.rect.x, key.rect.y + bob_y,
                                   key.rect.width, key.rect.height)
            if center_distance(player.rect, key_draw) < PICKUP_DISTANCE:
                key.collected  = True
                player.has_key = True

        if scene == "main" and player.has_key and not door_b.is_open:
            if center_distance(player.rect, door_b.rect) < DOOR_DISTANCE:
                door_b.is_open = True

        if door_b.is_open and not state["won"]:
            state["won"] = True
        if state["won"]:
            state["win_timer"] += dt

        cam_x      = state["cam_x"]
        cam_y      = state["cam_y"]
        target_cam = player.rect.centerx - CAM_THRESHOLD
        target_cam = max(0, min(target_cam, world_w - WIDTH))
        cam_x     += (target_cam - cam_x) * min(1.0, 8.0 * dt)
        state["cam_x"] = cam_x
        cx = int(cam_x)

        target_cam_y = player.rect.centery - HEIGHT // 2
        target_cam_y = max(-(HEIGHT // 2), min(target_cam_y, 0))
        cam_y += (target_cam_y - cam_y) * min(1.0, 8.0 * dt)
        state["cam_y"] = cam_y
        cy = int(cam_y)

        bg_offset = int(cx * 0.4) % WIDTH
        screen.blit(bg_scaled, (-bg_offset, 0))
        screen.blit(bg_scaled, (WIDTH - bg_offset, 0))

        for p in platforms:
            if p.kind == "wall":
                continue
            elif p.kind == "crate":
                screen.blit(crate_img, (p.rect.x - cx, p.rect.y - cy))
            elif p.kind == "ice":
                draw_tiled(screen, tile_ice, p.rect, cam_x=cx, cam_y=cy)
                pygame.draw.rect(screen, (180, 220, 240),
                    pygame.Rect(p.rect.x - cx, p.rect.y - cy, p.rect.width, p.rect.height), 2)
            else:
                tile = tile_floor if p.rect.height >= 60 else tile_thin
                draw_tiled(screen, tile, p.rect, cam_x=cx, cam_y=cy)
                pygame.draw.rect(screen, (80, 40, 10),
                    pygame.Rect(p.rect.x - cx, p.rect.y - cy, p.rect.width, p.rect.height), 2)

        for h in hazards:
            sx = int(h.x - cx)
            if h.kind == "spike":
                screen.blit(spike_img, (sx - 25, int(h.y) - 25 - cy))
            elif h.kind == "saw":
                rot = pygame.transform.rotate(saw_base, h.angle)
                screen.blit(rot, (sx - rot.get_width() // 2,
                                  int(h.y) - rot.get_height() // 2 - cy))

        screen.blit(door_img_open, (door_a.rect.x - cx, door_a.rect.y - cy))

        if scene == "key_zone" and not key.collected:
            kx = key_draw.x - cx
            screen.blit(key_img, (kx, key_draw.y - cy))
            glow = pygame.Surface((key_img.get_width() + 16, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 220, 50, 80), glow.get_rect())
            screen.blit(glow, (kx - 8, key_draw.bottom + 2 - cy))

        if scene == "main":
            screen.blit(door_img_open if door_b.is_open else door_img_closed,
                        (door_b.rect.x - cx, door_b.rect.y - cy))

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
        screen.blit(font.render("Kľúč: ANO" if player.has_key else "Kľúč: NIE",
                                True, (255, 220, 50)), (18, 15))
        screen.blit(font.render("Dvere: OTVORENÉ" if door_b.is_open else "Dvere: ZATVORENÉ",
                                True, (200, 200, 255)), (18, 38))

        if center_distance(player.rect, door_a.rect) < DOOR_DISTANCE:
            hint = font.render("[E] Vstúpiť / Vyjsť", True, (255, 255, 255))
            screen.blit(hint, (door_a.rect.x - cx, door_a.rect.y - cy - 30))

        hint_bg = pygame.Surface((400, 28), pygame.SRCALPHA)
        hint_bg.fill((0, 0, 0, 100))
        screen.blit(hint_bg, (10, HEIGHT - 38))
        screen.blit(font.render("← → pohyb  |  SPACE skok  |  R reštart",
                                True, (220, 220, 220)), (16, HEIGHT - 34))

        if state["fade_state"] is not None:
            ov = pygame.Surface((WIDTH, HEIGHT))
            ov.fill((0, 0, 0))
            ov.set_alpha(int(255 * state["fade_alpha"]))
            screen.blit(ov, (0, 0))

        if state["won"]:
            a = min(1.0, state["win_timer"] / 0.5)
            ov2 = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov2.fill((0, 0, 0, int(120 * a)))
            screen.blit(ov2, (0, 0))
            msg = font_big.render("Úroveň dokončená! Stlač R pre reštart.",
                                  True, (255, 255, 100))
            screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        pygame.display.flip()


if __name__ == "__main__":
    main()
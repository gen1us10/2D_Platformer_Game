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
ACCEL_ICE       = 700.0
DECEL_ICE       = 300.0

PICKUP_DISTANCE = 50
DOOR_DISTANCE   = 70
FLOOR_Y         = HEIGHT - 80
CAM_THRESHOLD   = WIDTH // 2
SAW_RADIUS      = 22

MAIN_WORLD_W = 1600
KEY_WORLD_W  = 3400


@dataclass
class Platform:
    rect: pygame.Rect
    friction: float
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


@dataclass
class PushBox:
    rect:          pygame.Rect
    spawn_x:       int
    spawn_y:       int
    vx:            float = 0.0
    vy:            float = 0.0
    on_ground:     bool  = False
    dead:          bool  = False
    respawn_timer: float = 0.0

BOX_RESPAWN_TIME = 4.0
BOX_SIZE         = 60


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
        Platform(pygame.Rect(0,           F, MAIN_WORLD_W, 80), FRICTION_NORMAL, "normal"),
        Platform(pygame.Rect(-20,         0, 20, HEIGHT),        FRICTION_NORMAL, "wall"),
        Platform(pygame.Rect(MAIN_WORLD_W,0, 20, HEIGHT),        FRICTION_NORMAL, "wall"),
    ]


def build_key_platforms():
    F = FLOOR_Y
    return [
        Platform(pygame.Rect(0,          F, KEY_WORLD_W, 80), FRICTION_NORMAL, "normal"),
        Platform(pygame.Rect(-20,        0, 20, HEIGHT),       FRICTION_NORMAL, "wall"),
        Platform(pygame.Rect(KEY_WORLD_W,0, 20, HEIGHT),       FRICTION_NORMAL, "wall"),

        Platform(pygame.Rect(350,  F - 140, 500, 22), 0.0, "ice"),
        Platform(pygame.Rect(950,  F - 320, 160, 22), FRICTION_NORMAL, "normal"),

        Platform(pygame.Rect(1200, F - 160, 280, 22), 0.0, "ice"),
        Platform(pygame.Rect(1580, F - 240, 160, 22), FRICTION_NORMAL, "normal"),

        Platform(pygame.Rect(1840, F - 160, 500, 22), 0.0, "ice"),

        Platform(pygame.Rect(2450, F - 280, 180, 22), FRICTION_NORMAL, "normal"),
        Platform(pygame.Rect(2720, F - 380, 600, 22), FRICTION_NORMAL, "normal"),
        Platform(pygame.Rect(2990, F - 380 - BOX_SIZE,     BOX_SIZE, BOX_SIZE), FRICTION_NORMAL, "crate"),
        Platform(pygame.Rect(2990, F - 380 - BOX_SIZE * 2, BOX_SIZE, BOX_SIZE), FRICTION_NORMAL, "crate"),
        Platform(pygame.Rect(2990, F - 380 - BOX_SIZE * 3, BOX_SIZE, BOX_SIZE), FRICTION_NORMAL, "crate"),
    ]


KEY_PLATFORM_IDX = 9


def build_key_hazards():
    F = FLOOR_Y
    floor_spikes = [Hazard(x, F - 25, "spike") for x in range(350, KEY_WORLD_W - 200, 50)]
    saws = [
        Hazard(2090, F - 160 - 24,       "saw"),
        Hazard(2090, F - 160 - 24 - 48,  "saw"),
        Hazard(2090, F - 160 - 24 - 96,  "saw"),
        Hazard(2090, F - 160 - 24 - 144, "saw"),
    ]
    return floor_spikes + saws


def build_key_pushboxes():
    F = FLOOR_Y
    plat_top = F - 380
    return [
        PushBox(
            rect    = pygame.Rect(360, F - 140 - BOX_SIZE, BOX_SIZE, BOX_SIZE),
            spawn_x = 360,
            spawn_y = F - 140 - BOX_SIZE,
        ),
        PushBox(
            rect    = pygame.Rect(1850, F - 160 - BOX_SIZE, BOX_SIZE, BOX_SIZE),
            spawn_x = 1850,
            spawn_y = F - 160 - BOX_SIZE,
        ),
        PushBox(
            rect    = pygame.Rect(2270, F - 160 - BOX_SIZE, BOX_SIZE, BOX_SIZE),
            spawn_x = 2270,
            spawn_y = F - 160 - BOX_SIZE,
        ),
        PushBox(
            rect    = pygame.Rect(2730, plat_top - BOX_SIZE, BOX_SIZE, BOX_SIZE),
            spawn_x = 2730,
            spawn_y = plat_top - BOX_SIZE,
        ),
        PushBox(
            rect    = pygame.Rect(3250, plat_top - BOX_SIZE, BOX_SIZE, BOX_SIZE),
            spawn_x = 3250,
            spawn_y = plat_top - BOX_SIZE,
        ),
    ]


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
    key_platforms  = build_key_platforms()
    key_hazards    = build_key_hazards()
    key_pushboxes  = build_key_pushboxes()

    kp  = key_platforms[KEY_PLATFORM_IDX]
    key = Key(rect=pygame.Rect(
        kp.rect.right - key_img.get_width() - 130,
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

    def reset_boxes():
        key_pushboxes.clear()
        key_pushboxes.extend(build_key_pushboxes())

    def do_respawn():
        player.rect.topleft = (220, FLOOR_Y - HB_H)
        player.vx = player.vy = 0.0
        state["cam_x"] = 0.0
        if state["scene"] == "key_zone":
            reset_boxes()
            if player.has_key:
                player.has_key = False
                key.collected  = False
                key.bob_timer  = 0.0

    def do_scene_switch():
        state["scene"] = state["scene_next"]
        player.rect.topleft = (220, FLOOR_Y - HB_H)
        player.vx = player.vy = 0.0
        state["cam_x"] = 0.0
        reset_boxes()

    def reset():
        player.rect.topleft = (220, FLOOR_Y - HB_H)
        player.vx = player.vy = 0.0
        player.on_ground = False
        player.has_key   = False
        key.collected    = False
        key.bob_timer    = 0.0
        door_b.is_open   = False
        reset_boxes()
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
        hazards   = key_hazards if scene == "key_zone" else []
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

        for b in key_pushboxes:
            if b.dead:
                continue
            if player.rect.colliderect(b.rect):
                overlap_x_left  = player.rect.right - b.rect.left
                overlap_x_right = b.rect.right - player.rect.left
                overlap_y_top   = player.rect.bottom - b.rect.top
                overlap_y_bot   = b.rect.bottom - player.rect.top
                min_x = min(overlap_x_left, overlap_x_right)
                min_y = min(overlap_y_top,  overlap_y_bot)
                if min_y < min_x:
                    if overlap_y_top < overlap_y_bot and player.vy >= 0:
                        player.rect.bottom = b.rect.top
                        player.on_ground   = True
                        player.vy          = 0
                    elif overlap_y_bot < overlap_y_top and player.vy < 0:
                        player.rect.top = b.rect.bottom
                        player.vy       = 0
                else:
                    if overlap_x_left < overlap_x_right and player.vx > 0:
                        b.vx = max(b.vx, player.vx * 0.4)
                        player.rect.right = b.rect.left
                    elif overlap_x_right < overlap_x_left and player.vx < 0:
                        b.vx = min(b.vx, player.vx * 0.4)
                        player.rect.left = b.rect.right

        standing_on_box = any(
            not b.dead and
            player.rect.bottom == b.rect.top and
            player.rect.right > b.rect.left and
            player.rect.left  < b.rect.right
            for b in key_pushboxes
        )

        if was_on_ground and not player.on_ground and not standing_on_box:
            player.coyote_timer = player.COYOTE_TIME

        ground_plat = get_ground_platform(player, platforms)
        if player.on_ground:
            if standing_on_box:
                apply_friction(player, dt, FRICTION_NORMAL)
            elif ground_plat and ground_plat.kind != "ice":
                apply_friction(player, dt, ground_plat.friction)

        player.update_jump(dt)

        if scene == "key_zone":
            boxes_to_remove = []
            boxes_to_add    = []

            for b in key_pushboxes:
                if b.dead:
                    b.respawn_timer -= dt
                    if b.respawn_timer <= 0:
                        boxes_to_add.append(PushBox(
                            rect    = pygame.Rect(b.spawn_x, b.spawn_y, BOX_SIZE, BOX_SIZE),
                            spawn_x = b.spawn_x,
                            spawn_y = b.spawn_y,
                        ))
                        boxes_to_remove.append(b)
                    continue

                b.vy += GRAVITY * dt

                b.rect.x += b.vx * dt
                for p in key_platforms:
                    if p.kind == "wall" or not b.rect.colliderect(p.rect):
                        continue
                    if b.vx > 0:
                        b.rect.right = p.rect.left
                        b.vx = 0.0
                    elif b.vx < 0:
                        b.rect.left = p.rect.right
                        b.vx = 0.0

                ground_p = None
                b.on_ground = False
                b.rect.y += b.vy * dt
                for p in key_platforms:
                    if p.kind == "wall" or p.kind == "crate" or not b.rect.colliderect(p.rect):
                        continue
                    if b.vy > 0:
                        b.rect.bottom = p.rect.top
                        b.on_ground   = True
                        b.vy          = 0
                        ground_p      = p
                    elif b.vy < 0:
                        b.rect.top = p.rect.bottom
                        b.vy       = 0

                if b.on_ground and ground_p:
                    decel = 150.0 if ground_p.kind == "ice" else 800.0
                    if b.vx > 0:
                        b.vx = max(0.0, b.vx - decel * dt)
                    elif b.vx < 0:
                        b.vx = min(0.0, b.vx + decel * dt)

                for h in key_hazards:
                    if h.kind == "spike":
                        if b.rect.colliderect(pygame.Rect(h.x - 20, h.y - 20, 40, 40)):
                            b.dead = True
                            b.respawn_timer = BOX_RESPAWN_TIME
                            break
                    elif h.kind == "saw":
                        if b.rect.colliderect(pygame.Rect(h.x - SAW_RADIUS, h.y - SAW_RADIUS, SAW_RADIUS * 2, SAW_RADIUS * 2)):
                            b.dead = True
                            b.respawn_timer = BOX_RESPAWN_TIME
                            break

                if not b.dead and (b.rect.top > FLOOR_Y + 50 or b.rect.right < 0 or b.rect.left > KEY_WORLD_W):
                    b.dead = True
                    b.respawn_timer = BOX_RESPAWN_TIME

            for b in boxes_to_remove:
                key_pushboxes.remove(b)
            key_pushboxes.extend(boxes_to_add)

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

        if scene == "key_zone":
            target_cam_y = player.rect.centery - HEIGHT // 2
            target_cam_y = max(-(HEIGHT // 2), min(target_cam_y, 0))
            cam_y += (target_cam_y - cam_y) * min(1.0, 8.0 * dt)
            state["cam_y"] = cam_y
        else:
            cam_y = 0.0
            state["cam_y"] = 0.0
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

        if scene == "key_zone":
            for b in key_pushboxes:
                if b.dead:
                    ghost = crate_img.copy()
                    ghost.set_alpha(60)
                    screen.blit(ghost, (b.spawn_x - cx, b.spawn_y - cy))
                    secs = int(b.respawn_timer) + 1
                    t = font.render(str(secs), True, (255, 255, 255))
                    screen.blit(t, (b.spawn_x - cx + BOX_SIZE // 2 - t.get_width() // 2,
                                    b.spawn_y - cy + BOX_SIZE // 2 - t.get_height() // 2))
                else:
                    screen.blit(crate_img, (b.rect.x - cx, b.rect.y - cy))

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
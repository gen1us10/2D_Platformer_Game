import pygame
from dataclasses import dataclass
import math

WIDTH, HEIGHT = 1280, 720
FPS = 60
WORLD_W = 3200  # ширина мира — в 2.5 раза шире экрана

ASSET_PLAYER      = "assets/player.png"
ASSET_BG          = "assets/bg.png"
ASSET_PLATFORM    = "assets/platform.png"
ASSET_KEY         = "assets/key.png"
ASSET_DOOR_CLOSED = "assets/door_closed.png"
ASSET_DOOR_OPEN   = "assets/door_open.png"

GRAVITY         = 1800.0
MOVE_SPEED      = 480.0
JUMP_SPEED      = 780.0
FRICTION_NORMAL = 12.0

PICKUP_DISTANCE = 50
DOOR_DISTANCE   = 60

FLOOR_Y = HEIGHT - 80

# камера начинает двигаться когда игрок за этой точкой по X на экране
CAM_THRESHOLD = WIDTH // 2


@dataclass
class Platform:
    rect: pygame.Rect
    friction: float
    restitution: float
    kind: str


@dataclass
class Player:
    rect: pygame.Rect
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    has_key: bool = False
    facing_right: bool = True

    def handle_input(self, keys):
        self.vx = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.vx = -MOVE_SPEED
            self.facing_right = False
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.vx = MOVE_SPEED
            self.facing_right = True

    def try_jump(self):
        if self.on_ground:
            self.vy = -JUMP_SPEED
            self.on_ground = False


@dataclass
class Key:
    rect: pygame.Rect
    collected: bool = False
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


def draw_tiled(surface, tile, area, cam_x=0):
    tw, th = tile.get_size()
    draw_rect = pygame.Rect(area.x - cam_x, area.y, area.width, area.height)
    prev_clip = surface.get_clip()
    surface.set_clip(draw_rect)
    for yy in range(draw_rect.top, draw_rect.bottom, th):
        for xx in range(draw_rect.left, draw_rect.right, tw):
            surface.blit(tile, (xx, yy))
    surface.set_clip(prev_clip)


def resolve_collisions_axis(player, platforms, axis):
    landed = None
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
                landed = p
            elif player.vy < 0:
                player.rect.top = p.rect.bottom
            player.vy = 0
    return landed


def apply_friction(player, dt, friction):
    if player.on_ground:
        player.vx *= max(0.0, 1.0 - friction * dt)


def center_distance(r1, r2):
    dx = r1.centerx - r2.centerx
    dy = r1.centery - r2.centery
    return math.sqrt(dx * dx + dy * dy)


def build_level_1():
    # Мир 3200px шириной. Платформы расположены лесенкой слева направо.
    # Ключ на платформе ~середине мира, дверь ближе к концу.
    platforms = [
        # пол и стены
        Platform(pygame.Rect(0,       FLOOR_Y, WORLD_W, 80), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(-20,     0, 20, HEIGHT),         FRICTION_NORMAL, 0.0, "wall"),
        Platform(pygame.Rect(WORLD_W, 0, 20, HEIGHT),         FRICTION_NORMAL, 0.0, "wall"),

        # --- секция 1: начало (0–800) ---
        Platform(pygame.Rect(180,  FLOOR_Y - 130, 200, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(420,  FLOOR_Y - 230, 180, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(640,  FLOOR_Y - 330, 220, 22), FRICTION_NORMAL, 0.0, "normal"),

        # --- секция 2: середина (800–1800) ---
        Platform(pygame.Rect(900,  FLOOR_Y - 180, 200, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(1100, FLOOR_Y - 300, 240, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(1350, FLOOR_Y - 400, 260, 22), FRICTION_NORMAL, 0.0, "normal"),  # ключ тут
        Platform(pygame.Rect(1600, FLOOR_Y - 260, 200, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(1820, FLOOR_Y - 150, 180, 22), FRICTION_NORMAL, 0.0, "normal"),

        # --- секция 3: конец (1900–3000) ---
        Platform(pygame.Rect(2050, FLOOR_Y - 250, 220, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(2300, FLOOR_Y - 370, 200, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(2520, FLOOR_Y - 220, 240, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(2780, FLOOR_Y - 310, 220, 22), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(2980, FLOOR_Y - 180, 200, 22), FRICTION_NORMAL, 0.0, "normal"),  # дверь тут
    ]
    return platforms

KEY_PLATFORM_IDX  = 8   # Rect(1350, ...)
DOOR_PLATFORM_IDX = 15  # Rect(2980, ...)


def main():
    pygame.init()
    screen   = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Level 1 – Gravitácia a základný pohyb")
    clock    = pygame.time.Clock()
    font     = pygame.font.SysFont("Arial", 20)
    font_big = pygame.font.SysFont("Arial", 36, bold=True)

    bg_scaled = pygame.transform.scale(load_image(ASSET_BG), (WIDTH, HEIGHT))

    platform_img = load_image(ASSET_PLATFORM)
    strip      = crop_image(platform_img, 0, 16, platform_img.get_width(), 64)
    tile_floor = pygame.transform.smoothscale(strip, (256, 80))
    tile_thin  = pygame.transform.smoothscale(strip, (256, 22))

    FRAME_W, FRAME_H = 64, 64
    SCALE  = 1.8
    sheet  = load_image(ASSET_PLAYER)
    img_r  = crop_frame(sheet, 0, 0, FRAME_W, FRAME_H, SCALE)
    img_l  = pygame.transform.flip(img_r, True, False)

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

    platforms = build_level_1()

    player = Player(rect=pygame.Rect(80, FLOOR_Y - HB_H, HB_W, HB_H))

    kp  = platforms[KEY_PLATFORM_IDX]
    key = Key(rect=pygame.Rect(
        kp.rect.centerx - key_img.get_width() // 2,
        kp.rect.top - key_img.get_height() - 20,
        key_img.get_width(), key_img.get_height()
    ))

    dp   = platforms[DOOR_PLATFORM_IDX]
    door = Door(rect=pygame.Rect(
        dp.rect.centerx - DOOR_W // 2,
        dp.rect.top - DOOR_H,
        DOOR_W, DOOR_H
    ))

    cam_x    = 0.0   # сколько мир сдвинут влево (мировые пиксели)
    won      = False
    win_timer = 0.0

    def reset():
        nonlocal cam_x, won, win_timer
        player.rect.topleft = (80, FLOOR_Y - HB_H)
        player.vx = player.vy = 0.0
        player.on_ground = False
        player.has_key = False
        key.collected = False
        door.is_open = False
        won = False
        win_timer = 0.0
        cam_x = 0.0

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
                    player.try_jump()

        player.handle_input(pygame.key.get_pressed())

        player.vy += GRAVITY * dt

        player.rect.x += int(player.vx * dt)
        resolve_collisions_axis(player, platforms, "x")

        player.on_ground = False
        player.rect.y += int(player.vy * dt)
        landed = resolve_collisions_axis(player, platforms, "y")

        if landed:
            apply_friction(player, dt, landed.friction)

        # --- камера ---
        # целевой cam_x: держим игрока у CAM_THRESHOLD от левого края экрана
        target_cam = player.rect.centerx - CAM_THRESHOLD
        target_cam = max(0, min(target_cam, WORLD_W - WIDTH))
        # плавное следование камеры
        cam_x += (target_cam - cam_x) * min(1.0, 8.0 * dt)
        cx = int(cam_x)

        # --- ключ ---
        key.bob_timer += dt
        bob_y    = int(math.sin(key.bob_timer * 3.0) * 5)
        key_draw = pygame.Rect(key.rect.x, key.rect.y + bob_y, key.rect.width, key.rect.height)

        if not key.collected and center_distance(player.rect, key_draw) < PICKUP_DISTANCE:
            key.collected = True
            player.has_key = True

        if player.has_key and not door.is_open:
            if center_distance(player.rect, door.rect) < DOOR_DISTANCE:
                door.is_open = True

        if door.is_open and not won:
            won = True

        if won:
            win_timer += dt

        # --- render ---
        # фон — рисуем дважды для эффекта параллакса (фон движется медленнее)
        bg_offset = int(cx * 0.4) % WIDTH
        screen.blit(bg_scaled, (-bg_offset, 0))
        screen.blit(bg_scaled, (WIDTH - bg_offset, 0))

        # платформы
        for p in platforms:
            if p.kind == "wall":
                continue
            tile = tile_floor if p.rect.height >= 60 else tile_thin
            draw_tiled(screen, tile, p.rect, cam_x=cx)
            outline = pygame.Rect(p.rect.x - cx, p.rect.y, p.rect.width, p.rect.height)
            pygame.draw.rect(screen, (80, 40, 10), outline, 2)

        # ключ
        if not key.collected:
            kx = key_draw.x - cx
            screen.blit(key_img, (kx, key_draw.y))
            glow = pygame.Surface((key_img.get_width() + 16, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 220, 50, 80), glow.get_rect())
            screen.blit(glow, (kx - 8, key_draw.bottom + 2))

        # дверь
        door_sprite = door_img_open if door.is_open else door_img_closed
        screen.blit(door_sprite, (door.rect.x - cx, door.rect.y))

        # игрок
        sprite = img_r if player.facing_right else img_l
        screen.blit(sprite, (player.rect.x - cx + SP_OX, player.rect.y + SP_OY))

        # UI (фиксированный — не двигается с камерой)
        ui_bg = pygame.Surface((300, 60), pygame.SRCALPHA)
        ui_bg.fill((0, 0, 0, 120))
        screen.blit(ui_bg, (10, 10))
        screen.blit(font.render("Kľúč: ÁNO"  if player.has_key else "Kľúč: NIE",
                                True, (255, 220, 50)),  (18, 15))
        screen.blit(font.render("Dvere: OTVORENÉ" if door.is_open else "Dvere: ZATVORENÉ",
                                True, (200, 200, 255)), (18, 38))

        info_bg = pygame.Surface((240, 56), pygame.SRCALPHA)
        info_bg.fill((0, 0, 0, 100))
        screen.blit(info_bg, (WIDTH - 250, 10))
        screen.blit(font.render(f"vx = {player.vx:+.0f} px/s", True, (180, 230, 255)), (WIDTH - 244, 14))
        screen.blit(font.render(f"vy = {player.vy:+.0f} px/s", True, (180, 230, 255)), (WIDTH - 244, 36))

        hint_bg = pygame.Surface((310, 28), pygame.SRCALPHA)
        hint_bg.fill((0, 0, 0, 100))
        screen.blit(hint_bg, (10, HEIGHT - 38))
        screen.blit(font.render("← → pohyb  |  SPACE skok  |  R reštart", True, (220, 220, 220)), (16, HEIGHT - 34))

        if won:
            alpha = min(1.0, win_timer / 0.5)
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(120 * alpha)))
            screen.blit(overlay, (0, 0))
            msg = font_big.render("Úroveň dokončená! Stlač R pre reštart.", True, (255, 255, 100))
            screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        pygame.display.flip()


if __name__ == "__main__":
    main()
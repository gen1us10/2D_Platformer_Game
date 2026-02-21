import pygame
from dataclasses import dataclass
import math

WIDTH, HEIGHT = 1280, 720
FPS = 60
WORLD_W = 3200

ASSET_PLAYER      = "assets/player.png"
ASSET_BG          = "assets/bg.png"
ASSET_PLATFORM    = "assets/platform.png"
ASSET_KEY         = "assets/key.png"
ASSET_DOOR_CLOSED = "assets/door_closed.png"
ASSET_DOOR_OPEN   = "assets/door_open.png"
ASSET_CRATE       = "assets/crate.png"
ASSET_SAW         = "assets/saw.png"
ASSET_SPIKE       = "assets/spike.png"

GRAVITY         = 1800.0
MOVE_SPEED      = 480.0
JUMP_SPEED      = 780.0
FRICTION_NORMAL = 12.0

PICKUP_DISTANCE = 50
DOOR_DISTANCE   = 60

FLOOR_Y       = HEIGHT - 80
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
    coyote_timer: float = 0.0
    jump_buffer: float = 0.0

    COYOTE_TIME      = 0.10
    JUMP_BUFFER_TIME = 0.10

    def handle_input(self, keys):
        self.vx = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.vx = -MOVE_SPEED
            self.facing_right = False
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.vx = MOVE_SPEED
            self.facing_right = True

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


def build_level_2():
    platforms = [
        Platform(pygame.Rect(0,       FLOOR_Y, WORLD_W, 80), FRICTION_NORMAL, 0.0, "normal"),
        Platform(pygame.Rect(-20,     0, 20, HEIGHT),         FRICTION_NORMAL, 0.0, "wall"),
        Platform(pygame.Rect(WORLD_W, 0, 20, HEIGHT),         FRICTION_NORMAL, 0.0, "wall"),
    ]
    return platforms


def main():
    pygame.init()
    screen   = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Level 2 – Kolízie s prekážkami (AABB)")
    clock    = pygame.time.Clock()
    font     = pygame.font.SysFont("Arial", 20)

    bg_scaled = pygame.transform.scale(load_image(ASSET_BG), (WIDTH, HEIGHT))

    platform_img = load_image(ASSET_PLATFORM)
    strip      = crop_image(platform_img, 0, 16, platform_img.get_width(), 64)
    tile_floor = pygame.transform.smoothscale(strip, (256, 80))
    tile_thin  = pygame.transform.smoothscale(strip, (256, 22))

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

    platforms = build_level_2()
    player    = Player(rect=pygame.Rect(80, FLOOR_Y - HB_H, HB_W, HB_H))

    cam_x      = 0.0
    anim_timer = 0.0
    anim_frame = 0

    def reset():
        nonlocal cam_x, anim_timer, anim_frame
        player.rect.topleft = (80, FLOOR_Y - HB_H)
        player.vx = player.vy = 0.0
        player.on_ground = False
        cam_x = 0.0
        anim_timer = 0.0
        anim_frame = 0

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

        player.handle_input(pygame.key.get_pressed())

        player.vy += GRAVITY * dt

        player.rect.x += int(player.vx * dt)
        resolve_collisions_axis(player, platforms, "x")

        was_on_ground = player.on_ground
        player.on_ground = False
        player.rect.y += int(player.vy * dt)
        landed = resolve_collisions_axis(player, platforms, "y")

        if was_on_ground and not player.on_ground:
            player.coyote_timer = player.COYOTE_TIME

        if landed:
            apply_friction(player, dt, landed.friction)

        player.update_jump(dt)

        target_cam = player.rect.centerx - CAM_THRESHOLD
        target_cam = max(0, min(target_cam, WORLD_W - WIDTH))
        cam_x += (target_cam - cam_x) * min(1.0, 8.0 * dt)
        cx = int(cam_x)

        bg_offset = int(cx * 0.4) % WIDTH
        screen.blit(bg_scaled, (-bg_offset, 0))
        screen.blit(bg_scaled, (WIDTH - bg_offset, 0))

        for p in platforms:
            if p.kind == "wall":
                continue
            tile = tile_floor if p.rect.height >= 60 else tile_thin
            draw_tiled(screen, tile, p.rect, cam_x=cx)
            pygame.draw.rect(screen, (80, 40, 10),
                             pygame.Rect(p.rect.x - cx, p.rect.y, p.rect.width, p.rect.height), 2)

        if player.vx != 0:
            anim_timer += dt
            if anim_timer >= 1.0 / 8:
                anim_timer -= 1.0 / 8
                anim_frame = (anim_frame + 1) % 4
        else:
            anim_timer = 0.0
            anim_frame = 0

        if player.vx > 0:
            sprite = walk_right[anim_frame]
        elif player.vx < 0:
            sprite = walk_left[anim_frame]
        else:
            sprite = img_idle

        screen.blit(sprite, (player.rect.x - cx + SP_OX, player.rect.y + SP_OY))

        hint_bg = pygame.Surface((310, 28), pygame.SRCALPHA)
        hint_bg.fill((0, 0, 0, 100))
        screen.blit(hint_bg, (10, HEIGHT - 38))
        screen.blit(font.render("← → pohyb  |  SPACE skok  |  R reštart", True, (220, 220, 220)), (16, HEIGHT - 34))

        pygame.display.flip()


if __name__ == "__main__":
    main()
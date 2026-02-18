import pygame
from dataclasses import dataclass

# ----------------------------
# Настройки
# ----------------------------
WIDTH, HEIGHT = 1000, 600
FPS = 60

ASSET_PLAYER = "assets/player.png"
ASSET_BG = "assets/bg.png"
ASSET_PLATFORM = "assets/platform.png"
ASSET_KEY = "assets/key.png"
ASSET_DOOR_CLOSED = "assets/door_closed.png"
ASSET_DOOR_OPEN = "assets/door_open.png"

# Физика
GRAVITY = 2200.0
MOVE_SPEED = 520.0
JUMP_SPEED = 860.0

# Поверхности
FRICTION_NORMAL = 10.0
REST_NORMAL = 0.0

# Расстояния для взаимодействия
PICKUP_DISTANCE = 40
DOOR_DISTANCE = 40

# ----------------------------
# Данные
# ----------------------------
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

    def handle_input(self, keys: pygame.key.ScancodeWrapper):
        target_vx = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            target_vx -= MOVE_SPEED
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            target_vx += MOVE_SPEED
        self.vx = target_vx

    def try_jump(self):
        if self.on_ground:
            self.vy = -JUMP_SPEED
            self.on_ground = False


@dataclass
class Key:
    rect: pygame.Rect
    collected: bool = False


@dataclass
class Door:
    rect: pygame.Rect
    is_open: bool = False


# ----------------------------
# Вспомогательные функции
# ----------------------------
def load_image(path: str) -> pygame.Surface:
    return pygame.image.load(path).convert_alpha()


def crop_frame(sheet: pygame.Surface, x: int, y: int, w: int, h: int, scale: float = 1.0) -> pygame.Surface:
    frame = pygame.Surface((w, h), pygame.SRCALPHA)
    frame.blit(sheet, (0, 0), pygame.Rect(x, y, w, h))
    if scale != 1.0:
        frame = pygame.transform.scale(frame, (int(w * scale), int(h * scale)))
    return frame


def crop_image(img: pygame.Surface, x: int, y: int, w: int, h: int) -> pygame.Surface:
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.blit(img, (0, 0), pygame.Rect(x, y, w, h))
    return out


def draw_tiled(surface: pygame.Surface, tile: pygame.Surface, area: pygame.Rect):
    tw, th = tile.get_width(), tile.get_height()
    prev_clip = surface.get_clip()
    surface.set_clip(area)
    for yy in range(area.top, area.bottom, th):
        for xx in range(area.left, area.right, tw):
            surface.blit(tile, (xx, yy))
    surface.set_clip(prev_clip)


def resolve_collisions_axis(player: Player, platforms: list[Platform], axis: str):
    landed_platform = None
    for p in platforms:
        if player.rect.colliderect(p.rect):
            if axis == "x":
                if player.vx > 0:
                    player.rect.right = p.rect.left
                elif player.vx < 0:
                    player.rect.left = p.rect.right
                player.vx = 0.0
            elif axis == "y":
                if player.vy > 0:
                    player.rect.bottom = p.rect.top
                    player.on_ground = True
                    landed_platform = p
                    player.vy = 0.0
                elif player.vy < 0:
                    player.rect.top = p.rect.bottom
                    player.vy = 0.0
    return landed_platform


def apply_friction(player: Player, dt: float, friction_value: float):
    if not player.on_ground:
        return
    k = max(0.0, friction_value)
    factor = max(0.0, 1.0 - k * dt)
    player.vx *= factor


def distance(rect1: pygame.Rect, rect2: pygame.Rect) -> float:
    """Расстояние между центрами двух rect"""
    cx1, cy1 = rect1.centerx, rect1.centery
    cx2, cy2 = rect2.centerx, rect2.centery
    return ((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2) ** 0.5


# ----------------------------
# Level 1
# ----------------------------
def build_level_1() -> list[Platform]:
    platforms = []
    # Пол
    platforms.append(Platform(pygame.Rect(0, HEIGHT - 60, WIDTH, 60), FRICTION_NORMAL, REST_NORMAL, "normal"))
    # Платформы (убрали платформу Rect(650, 520, 140, 25))
    platforms.append(Platform(pygame.Rect(150, 440, 260, 25), FRICTION_NORMAL, REST_NORMAL, "normal"))
    platforms.append(Platform(pygame.Rect(500, 340, 260, 25), FRICTION_NORMAL, REST_NORMAL, "normal"))
    platforms.append(Platform(pygame.Rect(820, 460, 160, 25), FRICTION_NORMAL, REST_NORMAL, "normal"))
    # Стены-коллайдеры
    platforms.append(Platform(pygame.Rect(-20, 0, 20, HEIGHT), FRICTION_NORMAL, REST_NORMAL, "normal"))
    platforms.append(Platform(pygame.Rect(WIDTH, 0, 20, HEIGHT), FRICTION_NORMAL, REST_NORMAL, "normal"))
    return platforms


# ----------------------------
# Main
# ----------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Level 1 – Gravitácia a základný pohyb")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 18)

    # --- assets ---
    bg_img = load_image(ASSET_BG)
    bg_scaled = pygame.transform.scale(bg_img, (WIDTH, HEIGHT))

    # platform texture
    platform_img = load_image(ASSET_PLATFORM)
    strip = crop_image(platform_img, 0, 16, platform_img.get_width(), 64)
    platform_tile_floor = pygame.transform.smoothscale(strip, (256, 60))
    platform_tile_thin = pygame.transform.smoothscale(strip, (256, 25))

    # player spritesheet
    player_sheet = load_image(ASSET_PLAYER)
    FRAME_W, FRAME_H = 64, 64
    SCALE = 1.5
    player_img = crop_frame(player_sheet, 0, 0, FRAME_W, FRAME_H, SCALE)

    # key image (315x250) - уменьшаем до разумного размера
    key_img = load_image(ASSET_KEY)
    key_img = pygame.transform.smoothscale(key_img, (60, 50))  # Маленький ключик

    # door images (512x768) - уменьшаем пропорционально
    door_closed_img = load_image(ASSET_DOOR_CLOSED)
    door_open_img = load_image(ASSET_DOOR_OPEN)
    door_width = 80
    door_height = int(768 * door_width / 512)
    door_closed_img = pygame.transform.smoothscale(door_closed_img, (door_width, door_height))
    door_open_img = pygame.transform.smoothscale(door_open_img, (door_width, door_height))

    # --- Создаём объекты ---
    platforms = build_level_1()
    player = Player(rect=pygame.Rect(60, 200, player_img.get_width(), player_img.get_height()))

    # Ключ на второй платформе (Rect(500, 340, 260, 25))
    key_platform = platforms[2]  # это платформа Rect(500, 340, 260, 25)
    key_x = key_platform.rect.centerx - key_img.get_width() // 2
    key_y = key_platform.rect.top - key_img.get_height() - 35  # 35 пикселей над платформой
    key = Key(rect=pygame.Rect(key_x, key_y, key_img.get_width(), key_img.get_height()))

    # Дверь на третьей платформе (Rect(820, 460, 160, 25))
    door_platform = platforms[3]  # это платформа Rect(820, 460, 160, 25)
    door_x = door_platform.rect.centerx - door_width // 2
    door_y = door_platform.rect.top - door_height
    door = Door(rect=pygame.Rect(door_x, door_y, door_width, door_height))

    running = True
    current_surface_kind = "air"

    while running:
        dt = clock.tick(FPS) / 1000.0

        # events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    player.rect.topleft = (60, 200)
                    player.vx, player.vy = 0.0, 0.0
                    player.on_ground = False
                    player.has_key = False
                    key.collected = False
                    door.is_open = False

                if event.key == pygame.K_SPACE:
                    player.try_jump()

        keys = pygame.key.get_pressed()
        player.handle_input(keys)

        # physics
        player.vy += GRAVITY * dt

        player.rect.x += int(player.vx * dt)
        resolve_collisions_axis(player, platforms, "x")

        player.on_ground = False
        player.rect.y += int(player.vy * dt)
        landed = resolve_collisions_axis(player, platforms, "y")

        if landed is not None:
            current_surface_kind = landed.kind
            apply_friction(player, dt, landed.friction)
        else:
            current_surface_kind = "air"

        # --- Логика ключа ---
        if not key.collected:
            if distance(player.rect, key.rect) < PICKUP_DISTANCE:
                key.collected = True
                player.has_key = True

        # --- Логика двери ---
        if player.has_key and not door.is_open:
            if distance(player.rect, door.rect) < DOOR_DISTANCE:
                door.is_open = True

        # render
        screen.blit(bg_scaled, (0, 0))

        # Рисуем платформы
        for p in platforms:
            if p.rect.x < 0 or p.rect.right > WIDTH:
                continue
            if p.rect.height >= 50:
                draw_tiled(screen, platform_tile_floor, p.rect)
            else:
                draw_tiled(screen, platform_tile_thin, p.rect)
            pygame.draw.rect(screen, (0, 0, 0), p.rect, 2)

        # Рисуем ключ (если не собран)
        if not key.collected:
            screen.blit(key_img, key.rect.topleft)

        # Рисуем дверь
        if door.is_open:
            screen.blit(door_open_img, door.rect.topleft)
        else:
            screen.blit(door_closed_img, door.rect.topleft)

        # Рисуем игрока
        screen.blit(player_img, player.rect.topleft)

        # Info
        info = [
            f"has_key={player.has_key}  door_open={door.is_open}",
        ]
        y = 10
        for line in info:
            screen.blit(font.render(line, True, (20, 20, 20)), (10, y))
            y += 22

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
import pygame
import sys
import math
import os

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

import level1
import level2
import level3
import level4
import level5

_LEVEL_MODULES = [level1, level2, level3, level4, level5]

WIDTH, HEIGHT = 1280, 720
FPS = 60

LEVELS = ["level1", "level2", "level3", "level4", "level5"]
LEVEL_NAMES = [
    "Gravitácia a základný pohyb",
    "Kolízie s prekážkami (AABB)",
    "Odraz od pružných platforiem",
    "Povrchy s rôznym trením",
    "Hmotnosť a manipulácia s objektmi",
]


def load_font(size, bold=False):
    return pygame.font.SysFont("Arial", size, bold=bold)


def draw_stars(surface, stars, t):
    for (x, y, r, speed, alpha) in stars:
        a = int(alpha * (0.7 + 0.3 * math.sin(t * speed)))
        pygame.draw.circle(surface, (a, a, a), (x, y), r)


def make_stars(n=80):
    import random
    random.seed(42)
    return [
        (random.randint(0, WIDTH), random.randint(0, HEIGHT),
         random.randint(1, 3), random.uniform(0.5, 2.5), random.randint(120, 255))
        for _ in range(n)
    ]


def draw_gradient_bg(surface):
    top_col    = (18, 14, 10)
    bottom_col = (45, 35, 22)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(top_col[0] + (bottom_col[0] - top_col[0]) * t)
        g = int(top_col[1] + (bottom_col[1] - top_col[1]) * t)
        b = int(top_col[2] + (bottom_col[2] - top_col[2]) * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (WIDTH, y))


def run_menu(screen, clock):
    font_title  = load_font(64, bold=True)
    font_sub    = load_font(20)
    font_level  = load_font(22, bold=True)
    font_hint   = load_font(18)

    stars     = make_stars()
    selected  = 0
    t         = 0.0
    unlocked  = 5

    bg = pygame.Surface((WIDTH, HEIGHT))
    draw_gradient_bg(bg)

    fade_alpha = 255
    fading_in  = True

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit", 0
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(LEVELS)
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(LEVELS)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected < unlocked:
                        return "play", selected
                if event.key == pygame.K_ESCAPE:
                    return "quit", 0
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                for i in range(len(LEVELS)):
                    r = _level_rect(i)
                    if r.collidepoint(mx, my) and i < unlocked:
                        return "play", i
            if event.type == pygame.MOUSEMOTION:
                mx, my = pygame.mouse.get_pos()
                for i in range(len(LEVELS)):
                    if _level_rect(i).collidepoint(mx, my):
                        selected = i

        screen.blit(bg, (0, 0))
        draw_stars(screen, stars, t)

        pulse = math.sin(t * 2.0) * 0.5 + 0.5
        title_col = (
            int(210 + 30 * pulse),
            int(170 + 20 * pulse),
            int(80 + 20 * pulse),
        )
        title_surf = font_title.render("2D Platformer", True, title_col)
        title_x = WIDTH // 2 - title_surf.get_width() // 2
        screen.blit(title_surf, (title_x, 60))

        sub = font_sub.render("Postupy implementácie fyzikálnych vlastností do hier", True, (160, 140, 100))
        screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 140))

        pygame.draw.line(screen, (100, 80, 50), (WIDTH // 2 - 300, 175), (WIDTH // 2 + 300, 175), 1)

        for i in range(len(LEVELS)):
            rect = _level_rect(i)
            is_sel = i == selected

            if is_sel:
                bg_col     = (70, 52, 28)
                border_col = (180, 140, 70)
            else:
                bg_col     = (35, 28, 18)
                border_col = (80, 65, 40)

            pygame.draw.rect(screen, bg_col, rect, border_radius=8)
            pygame.draw.rect(screen, border_col, rect, 2, border_radius=8)

            num = font_level.render(f"Level {i + 1}", True,
                                    (255, 200, 60) if is_sel else (160, 140, 100))
            name = font_hint.render(LEVEL_NAMES[i], True,
                                    (210, 190, 150) if is_sel else (110, 95, 70))
            screen.blit(num,  (rect.x + 20, rect.y + 10))
            screen.blit(name, (rect.x + 20, rect.y + 36))

        hint_texts = [
            "↑ ↓  vybrať úroveň",
            "ENTER  spustiť",
            "ESC  ukončiť",
        ]
        hx = WIDTH // 2
        hy = HEIGHT - 50
        hint_line = "   |   ".join(hint_texts)
        hint_surf = font_hint.render(hint_line, True, (110, 95, 70))
        screen.blit(hint_surf, (hx - hint_surf.get_width() // 2, hy))

        if fading_in:
            fade_alpha = max(0, fade_alpha - 8)
            if fade_alpha == 0:
                fading_in = False
        if fade_alpha > 0:
            ov = pygame.Surface((WIDTH, HEIGHT))
            ov.fill((0, 0, 0))
            ov.set_alpha(fade_alpha)
            screen.blit(ov, (0, 0))

        pygame.display.flip()


def _level_rect(i):
    total_h   = len(LEVELS) * 70 + (len(LEVELS) - 1) * 10
    start_y   = HEIGHT // 2 - total_h // 2 + 20
    x         = WIDTH // 2 - 350
    y         = start_y + i * 80
    return pygame.Rect(x, y, 700, 65)


def run_level(screen, clock, level_idx):
    mod = _LEVEL_MODULES[level_idx]
    result = mod.run(screen, clock)
    return result


def run_win_screen(screen, clock, level_idx):
    font_big  = load_font(52, bold=True)
    font_med  = load_font(26)
    font_hint = load_font(20)

    stars = make_stars(120)
    bg    = pygame.Surface((WIDTH, HEIGHT))
    draw_gradient_bg(bg)

    t          = 0.0
    fade_alpha = 255

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_m:
                    return "menu"
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_n):
                    if level_idx < len(LEVELS) - 1:
                        return "next"
                    return "menu"

        screen.blit(bg, (0, 0))
        draw_stars(screen, stars, t)

        pulse = math.sin(t * 2.5) * 0.5 + 0.5
        col = (int(210 + 30 * pulse), int(170 + 20 * pulse), int(60 + 20 * pulse))
        msg = font_big.render("Úroveň dokončená!", True, col)
        screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 100))

        lvl_name = font_med.render(
            f"Level {level_idx + 1}: {LEVEL_NAMES[level_idx]}", True, (180, 155, 110))
        screen.blit(lvl_name, (WIDTH // 2 - lvl_name.get_width() // 2, HEIGHT // 2 - 20))

        if level_idx < len(LEVELS) - 1:
            next_txt = font_hint.render(
                "ENTER — ďalší level  |  M — hlavné menu",
                True, (140, 120, 80))
        else:
            next_txt = font_hint.render(
                "Všetky úrovne dokončené!  ENTER / M — hlavné menu",
                True, (220, 180, 60))
        screen.blit(next_txt, (WIDTH // 2 - next_txt.get_width() // 2, HEIGHT // 2 + 60))

        fade_alpha = max(0, fade_alpha - 8)
        if fade_alpha > 0:
            ov = pygame.Surface((WIDTH, HEIGHT))
            ov.fill((0, 0, 0))
            ov.set_alpha(fade_alpha)
            screen.blit(ov, (0, 0))

        pygame.display.flip()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("2D Platformer")
    clock  = pygame.time.Clock()

    current_level = 0
    app_state     = "menu"

    while True:
        if app_state == "menu":
            action, level_idx = run_menu(screen, clock)
            if action == "quit":
                break
            if action == "play":
                current_level = level_idx
                app_state     = "level"

        elif app_state == "level":
            result = run_level(screen, clock, current_level)
            if result == "quit":
                break
            elif result == "menu":
                app_state = "menu"
            elif result == "won":
                app_state = "win"

        elif app_state == "win":
            result = run_win_screen(screen, clock, current_level)
            if result == "quit":
                break
            elif result == "menu":
                app_state = "menu"
            elif result == "next":
                current_level += 1
                app_state      = "level"

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
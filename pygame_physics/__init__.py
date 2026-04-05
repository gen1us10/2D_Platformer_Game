import pygame
import math
from dataclasses import dataclass

GRAVITY         = 1800.0
MOVE_SPEED      = 480.0
JUMP_SPEED      = 780.0
FRICTION_NORMAL = 12.0
ACCEL_ICE       = 700.0
DECEL_ICE       = 300.0


@dataclass
class Platform:
    rect: pygame.Rect
    friction: float = FRICTION_NORMAL
    restitution: float = 0.0
    kind: str = "normal"


@dataclass
class Player:
    rect: pygame.Rect
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    facing_right: bool = True
    coyote_timer: float = 0.0
    jump_buffer: float = 0.0
    has_key: bool = False

    COYOTE_TIME: float = 0.10
    JUMP_BUFFER_TIME: float = 0.10

    def handle_input(self, keys, dt: float = 0.0, on_ice: bool = False,
                     move_speed: float = MOVE_SPEED):
        left  = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]

        if on_ice:
            if left:
                self.vx = max(-move_speed, self.vx - ACCEL_ICE * dt)
                self.facing_right = False
            elif right:
                self.vx = min(move_speed, self.vx + ACCEL_ICE * dt)
                self.facing_right = True
            else:
                if self.vx > 0:
                    self.vx = max(0.0, self.vx - DECEL_ICE * dt)
                elif self.vx < 0:
                    self.vx = min(0.0, self.vx + DECEL_ICE * dt)
        else:
            if left:
                self.vx = -move_speed
                self.facing_right = False
            elif right:
                self.vx = move_speed
                self.facing_right = True
            else:
                self.vx = 0.0

    def request_jump(self):
        self.jump_buffer = self.JUMP_BUFFER_TIME

    def update_jump(self, dt: float, jump_speed: float = JUMP_SPEED):
        self.jump_buffer  = max(0.0, self.jump_buffer  - dt)
        self.coyote_timer = max(0.0, self.coyote_timer - dt)
        if self.jump_buffer > 0 and (self.on_ground or self.coyote_timer > 0):
            self.vy           = -jump_speed
            self.on_ground    = False
            self.coyote_timer = 0.0
            self.jump_buffer  = 0.0

    def apply_gravity(self, dt: float, gravity: float = GRAVITY):
        self.vy += gravity * dt


def resolve_collisions_axis(entity, platforms: list, axis: str):
    landed = None
    for p in platforms:
        if not entity.rect.colliderect(p.rect):
            continue
        if axis == "x":
            if entity.vx > 0:
                entity.rect.right = p.rect.left
            elif entity.vx < 0:
                entity.rect.left  = p.rect.right
            entity.vx = 0
        else:
            if entity.vy > 0:
                entity.rect.bottom = p.rect.top
                entity.on_ground   = True
                landed             = p
            elif entity.vy < 0:
                entity.rect.top = p.rect.bottom
            entity.vy = 0
    return landed


def apply_friction(entity, dt: float, friction: float = FRICTION_NORMAL):
    if entity.on_ground:
        entity.vx *= max(0.0, 1.0 - friction * dt)


def center_distance(r1: pygame.Rect, r2: pygame.Rect) -> float:
    dx = r1.centerx - r2.centerx
    dy = r1.centery - r2.centery
    return math.sqrt(dx * dx + dy * dy)


def step_player(player: Player, platforms: list, dt: float,
                gravity: float = GRAVITY,
                jump_speed: float = JUMP_SPEED):
    player.apply_gravity(dt, gravity)

    player.rect.x    += int(player.vx * dt)
    resolve_collisions_axis(player, platforms, "x")

    was_on_ground    = player.on_ground
    player.on_ground = False
    player.rect.y   += int(player.vy * dt)
    landed           = resolve_collisions_axis(player, platforms, "y")

    if was_on_ground and not player.on_ground:
        player.coyote_timer = player.COYOTE_TIME

    if landed:
        apply_friction(player, dt, landed.friction)

    player.update_jump(dt, jump_speed)

    return landed
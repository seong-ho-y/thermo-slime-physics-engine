import pygame
import random


class Particle:
    def __init__(self, position, mass=1.0):
        self.pos = pygame.Vector2(position)
        self.vel = pygame.Vector2(random.uniform(-10, 10), random.uniform(-10, 10))
        self.force = pygame.Vector2(0, 0)
        self.mass = mass
        self.radius = 6

    def apply_force(self, f: pygame.Vector2):
        self.force += f

    def mouse_collision(self, mouse_pos, radius=40, strength=200):
        delta = self.pos - mouse_pos
        dist = delta.length()

        if dist < radius:
            if dist == 0:
                dist = 0.01

            direction = delta / dist

            # falloff 기반 힘 (0~1)
            falloff = (radius - dist) / radius

            # 🔹 falloff^2 로 곡선화 → 가까운 거리에서도 급팽창 방지
            falloff = falloff ** 3

            # 힘 계산
            F = direction * falloff * strength

            # 🔹 안전 장치: force clamp
            max_force = strength * 1.2   # 필요하면 1.0~2.0 사이로 조절
            if F.length() > max_force:
                F = F.normalize() * max_force

            self.apply_force(F)

    def update(self, dt: float, temperature: float):
        # 가속도
        acc = self.force / self.mass

        # Semi-implicit Euler
        self.vel += acc * dt
        self.pos += self.vel * dt

        # 온도에 따른 damping (차가울수록 잘 안 흔들림)
        if temperature < 10.0:
            damping = 0.96
        elif temperature > 30.0:
            damping = 0.985
        else:
            damping = 0.975

        self.vel *= damping

        # 간단한 화면 경계 충돌 (800x600 가정)
        if self.pos.x < self.radius:
            self.pos.x = self.radius
            self.vel.x *= -0.5
        elif self.pos.x > 800 - self.radius:
            self.pos.x = 800 - self.radius
            self.vel.x *= -0.5

        if self.pos.y < self.radius:
            self.pos.y = self.radius
            self.vel.y *= -0.5
        elif self.pos.y > 600 - self.radius:
            self.pos.y = 600 - self.radius
            self.vel.y *= -0.5

        # 힘 리셋
        self.force = pygame.Vector2(0, 0)

    def render(self, screen):
        pygame.draw.circle(screen, (200, 200, 255), self.pos, self.radius)

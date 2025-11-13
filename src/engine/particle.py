import pygame
import random

class Particle:
    def __init__(self, position, mass = 1.0):
        self.pos = pygame.Vector2(position)
        self.vel = pygame.Vector2(random.uniform(-20, 20), random.uniform(-20, 20))
        self.mass = mass
        self.radius = 12

    def update(self, dt, temperature):
        damping = max(0.92 - (temperature - 20) * 0.01, 0.85)
        self.vel *= damping
        self.pos += self.vel * dt * 60 # 프레임 스케일 보정


        # 경계 충돌
        if self.pos.x < self.radius or self.pos.x > 800 - self.radius:
            self.vel.x *= -0.8
        if self.pos.y < self.radius or self.pos.y > 600 - self.radius:
            self.vel.y *= -0.8

    def render(self, screen):
        pygame.draw.circle(screen, (200, 180, 255), (int(self.pos.x), int(self.pos.y)), self.radius)
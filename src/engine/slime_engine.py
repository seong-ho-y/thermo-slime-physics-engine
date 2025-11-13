import pygame
from .slime import Slime

class SlimeEngine:
    def __init__(self, screen):
        self.screen = screen
        self.slimes = []

        center = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)
        self.slimes.append(Slime(center))

    def update(self, dt: float):
        for slime in self.slimes:
            slime.update(dt)

    def render(self):
        for slime in self.slimes:
            slime.render(self.screen)
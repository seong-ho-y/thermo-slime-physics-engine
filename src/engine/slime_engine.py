import pygame
from .slime import Slime


class SlimeEngine:
    def __init__(self, screen):
        self.screen = screen
        self.slimes = []

        center = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)
        self.slimes.append(Slime(center))

    def update(self, dt):
        mouse_pos = pygame.Vector2(pygame.mouse.get_pos())
        for slime in self.slimes:
            slime.update(dt, mouse_pos)

    def render(self):
        for slime in self.slimes:
            slime.render(self.screen)

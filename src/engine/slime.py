import pygame
from .particle import Particle
from .temperature import TemperatureSystem

class Slime:
    def __init__(self, position: pygame.Vector2):
        self.particles = []
        self.temperature = TemperatureSystem()

        self.particles.append(Particle(position, mass = 1.0))

    def update(self, dt: float):
        temp = self.temperature.get_current_temperature()
        for p in self.particles:
            p.update(dt, temp)

    def render(self, screen):
        for p in self.particles:
            p.render(screen)
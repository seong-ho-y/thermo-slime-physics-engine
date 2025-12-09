import pygame
import math


class Spring:
    def __init__(self, p1, p2, rest_length, k=50.0, damping=1.5):
        self.p1 = p1
        self.p2 = p2
        self.rest_length0 = rest_length  # 원래 길이 저장
        self.k0 = k
        self.damping = damping

    def apply(self, dt, temperature: float):
        delta = self.p2.pos - self.p1.pos
        dist = delta.length()
        if dist == 0:
            return
        direction = delta / dist

        # 온도에 따른 수축 (T 낮을수록 길이 줄어듦 -> 단단해짐)
        if temperature >= 10.0:
            shrink = 1.0
        elif temperature <= 0.0:
            shrink = 0.7
        else:
            # 10~0 사이 선형 보간
            t = (10.0 - temperature) / 10.0  # 0~1
            shrink = 1.0 - 0.3 * t

        rest_length = self.rest_length0 * shrink

        # 온도에 따라 k 약간만 변경
        if temperature < 10.0:
            k = self.k0 * 1.2
        elif temperature > 30.0:
            k = self.k0 * 0.8
        else:
            k = self.k0

        k = max(20.0, min(k, 80.0))

        spring_force = -k * (dist - rest_length)

        rel_vel = (self.p2.vel - self.p1.vel).dot(direction)
        damping_force = -self.damping * rel_vel

        force = (spring_force + damping_force) * direction

        # 힘 클램프
        max_force = 200.0
        length = force.length()
        if length > max_force:
            force *= (max_force / length)

        self.p1.apply_force(-force)
        self.p2.apply_force(force)

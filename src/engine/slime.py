import pygame
from .particle import Particle
from .spring import Spring
from .temperature import TemperatureSystem
import math


class Slime:
    def __init__(self, center: pygame.Vector2):
        self.temperature = TemperatureSystem()

        self.particles = []
        self.springs = []

        # Rigid body용 중심/속도/회전
        self.center_pos = pygame.Vector2(center)
        self.center_vel = pygame.Vector2(0, 0)

        self.angle = 0.0
        self.angular_vel = 0.0

        self.mass = 20.0
        self.inertia = 5000.0

        self.is_rigid = False
        self.rigid_offsets = None
        self.rigid_radius = 0.0

        # 파티클 개수
        count = 48
        radius = 60
        for i in range(count):
            ang = (2 * math.pi / count) * i
            px = center.x + math.cos(ang) * radius
            py = center.y + math.sin(ang) * radius
            self.particles.append(Particle(pygame.Vector2(px, py)))

        # 바깥 링 스프링
        for i in range(count):
            p1 = self.particles[i]
            p2 = self.particles[(i + 1) % count]
            rest = (p2.pos - p1.pos).length()
            self.springs.append(Spring(p1, p2, rest, k=50.0))

        # 대각선 스프링 (안정성/탱탱함)
        for i in range(count):
            p1 = self.particles[i]
            p2 = self.particles[(i + 2) % count]
            rest = (p2.pos - p1.pos).length()
            self.springs.append(Spring(p1, p2, rest, k=30.0))

        # 초기 원형 모양 저장 (for Shape Matching)
        init_center = self.compute_center()
        self.rest_offsets = [p.pos - init_center for p in self.particles]
        self.base_radius = sum(off.length() for off in self.rest_offsets) / len(self.rest_offsets)

    # ===========================
    # 기본 유틸
    # ===========================
    def compute_center(self):
        return sum((p.pos for p in self.particles), pygame.Vector2()) / len(self.particles)

    def compute_rigid_radius(self):
        dists = [off.length() for off in self.rigid_offsets]
        return sum(dists) / len(dists)

    def _compute_soft_center_blend(self, temp: float):
        """
        온도에 따라 파티클/센터 힘 비율 결정
        temp > 25   : 매우 말랑 → 파티클 위주 (0.8 / 0.2)
        10~25 사이  : 점점 덩어리 느낌 (선형 보간)
        0~10 사이   : 거의 덩어리 (0.0~0.2 / 1.0~0.8)
        """
        if temp >= 25.0:
            soft_factor = 0.8
        elif temp > 10.0:
            t = (temp - 10.0) / 15.0  # 0~1
            soft_factor = 0.2 + 0.6 * t
        else:  # 0 < temp <= 10
            t = max(0.0, temp / 10.0)
            soft_factor = 0.2 * t

        soft_factor = max(0.0, min(soft_factor, 1.0))
        center_factor = 1.0 - soft_factor
        return soft_factor, center_factor

    def _shape_matching(self, temp: float):
        """
        Soft / Semi 상태에서 원형을 유지하려는 형태 복원 단계.
        현재 center 기준으로 각 파티클을 '목표 원' 방향으로 살짝씩 당긴다.
        """
        center = self.compute_center()
        self.center_pos = pygame.Vector2(center)

        # 온도에 따른 목표 반경 (차가울수록 살짝 수축)
        if temp >= 10.0:
            shrink = 1.0
        elif temp <= 0.0:
            shrink = 0.7
        else:
            t = temp / 10.0           # 0~1
            shrink = 0.7 + 0.3 * t    # 0.7 ~ 1.0

        target_radius = self.base_radius * shrink

        # 온도에 따른 형태 복원 강도
        if temp >= 25.0:
            stiffness = 0.05   # 매우 말랑
        elif temp > 10.0:
            stiffness = 0.12   # 중간
        else:  # 0 < temp <= 10
            stiffness = 0.25   # 단단

        for p in self.particles:
            rel = p.pos - center
            dist = rel.length()
            if dist == 0:
                continue
            desired = center + (rel / dist) * target_radius
            p.pos = p.pos.lerp(desired, stiffness)

    # ===========================
    # Convex Hull Utility
    # ===========================
    def _closest_point_on_segment(self, a: pygame.Vector2, b: pygame.Vector2, p: pygame.Vector2) -> pygame.Vector2:
        """
        선분 AB 위에서 점 P와 가장 가까운 점을 구함
        """
        ab = b - a
        ab_len2 = ab.length_squared()
        if ab_len2 == 0:
            return pygame.Vector2(a)
        t = (p - a).dot(ab) / ab_len2
        t = max(0.0, min(1.0, t))
        return a + ab * t

    def _compute_convex_hull(self):
        """
        Convex Hull을 (particle_index, pos) 형태로 반환.
        """
        pts = [(i, p.pos) for i, p in enumerate(self.particles)]
        pts_sorted = sorted(pts, key=lambda x: (x[1].x, x[1].y))

        def cross(o, a, b):
            return (a[1].x - o[1].x) * (b[1].y - o[1].y) - (a[1].y - o[1].y) * (b[1].x - o[1].x)

        lower = []
        for p in pts_sorted:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)

        upper = []
        for p in reversed(pts_sorted):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)

        hull = lower[:-1] + upper[:-1]
        return hull  # [(index, pos), ...]

    # ===========================
    # MAIN UPDATE
    # ===========================
    def update(self, dt, mouse_pos):
        temp = self.temperature.get_current_temperature()
        mouse_pos = pygame.Vector2(mouse_pos)

        # =========================
        # RIGID 모드 판단
        # =========================
        if temp <= 0.0:
            if not self.is_rigid:
                center = self.compute_center()
                self.center_pos = pygame.Vector2(center)
                self.rigid_offsets = [p.pos - center for p in self.particles]

                # 평균 반경 (circle 근사용)
                self.rigid_radius = self.compute_rigid_radius()

                # 속도 초기화
                for p in self.particles:
                    p.vel = pygame.Vector2(0, 0)
                self.center_vel = pygame.Vector2(0, 0)
                self.angular_vel = 0.0

            self.is_rigid = True
        else:
            if self.is_rigid:
                self.is_rigid = False
                self.rigid_offsets = None

        # =========================
        # SOFT / SEMIRIGID
        # =========================
        if not self.is_rigid:
            soft_factor, center_factor = self._compute_soft_center_blend(temp)

            # 현재 중심
            center = self.compute_center()
            self.center_pos = pygame.Vector2(center)

            # 1) Convex Hull 기반 마우스 충돌
            center_force = pygame.Vector2(0, 0)
            mouse_radius = 40
            base_strength = 700.0

            hull = self._compute_convex_hull()
            if len(hull) >= 2:
                for k in range(len(hull)):
                    i1, p1 = hull[k]
                    i2, p2 = hull[(k + 1) % len(hull)]

                    closest = self._closest_point_on_segment(p1, p2, mouse_pos)
                    delta = closest - mouse_pos
                    dist = delta.length()

                    if dist < mouse_radius:
                        if dist == 0:
                            dist = 0.01
                        direction = delta / dist

                        falloff = (mouse_radius - dist) / mouse_radius
                        falloff = falloff * falloff  # 부드러운 감소

                        F = direction * falloff * base_strength

                        max_force = base_strength * 1.2
                        if F.length() > max_force:
                            F = F.normalize() * max_force

                        # (1) edge 두 파티클에 힘 분배 -> 표면이 먼저 찌그러짐
                        if soft_factor > 0.0:
                            self.particles[i1].apply_force(F * soft_factor * 0.7)
                            self.particles[i2].apply_force(F * soft_factor * 0.7)

                            # (2) edge 중간점 근처 파티클에도 추가 분배 -> 더 깊은 local 변형
                            mid = (p1 + p2) * 0.5
                            for pi, pp in enumerate(self.particles):
                                if (pp.pos - mid).length() < 15.0:
                                    self.particles[pi].apply_force(F * soft_factor * 0.5)

                        # (3) center에도 일부 힘 적용 -> 덩어리 전체 이동
                        if center_factor > 0.0:
                            center_force += F * center_factor

            # 2) 슬라임 중심 이동
            acc_center = center_force / self.mass
            self.center_vel += acc_center * dt
            self.center_vel *= 0.98
            center_shift = self.center_vel * dt

            for p in self.particles:
                p.pos += center_shift

            # 3) 스프링 힘 적용
            for s in self.springs:
                s.apply(dt, temp)

            # 4) 파티클 업데이트
            for p in self.particles:
                p.update(dt, temp)

            # 5) Soft/Semi-Rigid 전용 벽 충돌 보정
            radius = self.base_radius * 1.1

            screen_w = 800
            screen_h = 600

            cx, cy = self.center_pos.x, self.center_pos.y
            shift = pygame.Vector2(0, 0)

            if cx < radius:
                shift.x = radius - cx
            elif cx > screen_w - radius:
                shift.x = (screen_w - radius) - cx

            if cy < radius:
                shift.y = radius - cy
            elif cy > screen_h - radius:
                shift.y = (screen_h - radius) - cy

            if shift.length_squared() > 0:
                self.center_pos += shift
                for p in self.particles:
                    p.pos += shift

            # 6) 형태 복원 – 원형으로 돌아가려는 힘
            self._shape_matching(temp)

            return

        # =========================
        # RIGID-BODY (Circle + Rotation)
        # =========================
        total_force = pygame.Vector2(0, 0)
        total_torque = 0.0

        delta = self.center_pos - mouse_pos
        dist = delta.length()

        radius = self.rigid_radius
        mouse_influence_radius = radius + 40

        if dist < mouse_influence_radius:
            if dist == 0:
                dist = 0.01
            normal = delta / dist
            penetration = mouse_influence_radius - dist

            strength = 1500.0
            F = normal * penetration * strength
            total_force += F

            collision_point = self.center_pos - normal * radius
            r = collision_point - self.center_pos
            torque = r.x * F.y - r.y * F.x
            total_torque += torque

        # 선형 운동
        acc = total_force / self.mass
        self.center_vel += acc * dt
        self.center_vel *= 0.98
        self.center_pos += self.center_vel * dt

        # 화면 경계 처리
        if self.center_pos.x < radius:
            self.center_pos.x = radius
            self.center_vel.x *= -0.4
        elif self.center_pos.x > 800 - radius:
            self.center_pos.x = 800 - radius
            self.center_vel.x *= -0.4

        if self.center_pos.y < radius:
            self.center_pos.y = radius
            self.center_vel.y *= -0.4
        elif self.center_pos.y > 600 - radius:
            self.center_pos.y = 600 - radius
            self.center_vel.y *= -0.4

        # 회전 운동
        angular_acc = total_torque / self.inertia
        self.angular_vel += angular_acc * dt
        self.angular_vel *= 0.97
        self.angle += self.angular_vel * dt

        # 파티클 위치 재생성 (center + 회전된 offset)
        cos_a = math.cos(self.angle)
        sin_a = math.sin(self.angle)

        for i, off in enumerate(self.rigid_offsets):
            rotated = pygame.Vector2(
                off.x * cos_a - off.y * sin_a,
                off.x * sin_a + off.y * cos_a
            )
            self.particles[i].pos = self.center_pos + rotated

    # ===========================
    # RENDER
    # ===========================
    def render(self, screen):
        # Soft/세미일 때 스프링 시각화
        if not self.is_rigid:
            for s in self.springs:
                pygame.draw.line(screen, (120, 120, 200), s.p1.pos, s.p2.pos, 1)

        # 마우스 충돌 범위 시각화
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.circle(screen, (255, 100, 100), mouse_pos, 40, 1)

        # 파티클 그리기
        for p in self.particles:
            p.render(screen)

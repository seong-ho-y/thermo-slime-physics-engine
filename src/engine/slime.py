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

        # 🔹 더 많은 파티클로 부드러운 슬라임
        count = 32
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

        # 🔹 초기 원형 모양 저장 (Shape Matching용)
        init_center = self.compute_center()
        self.rest_offsets = [p.pos - init_center for p in self.particles]
        self.base_radius = sum(off.length() for off in self.rest_offsets) / len(self.rest_offsets)

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
        0~10 사이   : 거의 덩어리 (0.2 / 0.8 → 0에 가까워짐)
        """
        if temp >= 25.0:
            soft_factor = 0.8
        elif temp > 10.0:
            # 10~25 구간 선형 보간
            t = (temp - 10.0) / 15.0  # 0~1
            soft_factor = 0.2 + 0.6 * t
        else:  # 0 < temp <= 10
            # 0~10에서 0.0~0.2로 선형 증가
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
            # 0~10°C : 0.7 ~ 1.0 사이 선형
            t = temp / 10.0
            shrink = 0.7 + 0.3 * t

        target_radius = self.base_radius * shrink

        # 온도에 따른 형태 복원 강도
        if temp >= 25.0:
            stiffness = 0.05   # 매우 말랑 → 거의 안 당김
        elif temp > 10.0:
            stiffness = 0.12   # 중간 정도
        else:  # 0 < temp <= 10
            stiffness = 0.25   # 거의 덩어리 → 꽤 강하게 원형 유지

        # 각 파티클을 목표 원형에 조금씩 끌어당김
        for p in self.particles:
            rel = p.pos - center
            dist = rel.length()
            if dist == 0:
                continue
            # 방향은 유지, 거리만 target_radius에 가깝게
            desired = center + (rel / dist) * target_radius
            p.pos = p.pos.lerp(desired, stiffness)

    # ===========================
    # MAIN UPDATE
    # ===========================
    def update(self, dt, mouse_pos):
        temp = self.temperature.get_current_temperature()

        # =========================
        # RIGID 모드 판단
        # =========================
        if temp <= 0.0:
            # Rigid 모드 진입 처리
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
            # Soft / Semi-Rigid
            if self.is_rigid:
                # 막 Rigid에서 나왔다면 플래그 정리
                self.is_rigid = False
                self.rigid_offsets = None

        # =========================
        # SOFT / SEMI-RIGID
        # =========================
        if not self.is_rigid:
            # 온도 기반 블렌딩 비율
            soft_factor, center_factor = self._compute_soft_center_blend(temp)

            # 현재 중심
            center = self.compute_center()
            self.center_pos = pygame.Vector2(center)

            # 1) 마우스 충돌 → 파티클/센터 하이브리드 force
            center_force = pygame.Vector2(0, 0)

            mouse_radius = 40
            base_strength = 2000.0

            for p in self.particles:
                delta = p.pos - mouse_pos
                dist = delta.length()
                if dist < mouse_radius:
                    if dist == 0:
                        dist = 0.01
                    direction = delta / dist
                    penetration = mouse_radius - dist

                    F = direction * penetration * base_strength

                    # 일부는 파티클에, 일부는 슬라임 중심에
                    if soft_factor > 0.0:
                        p.apply_force(F * soft_factor)
                    if center_factor > 0.0:
                        center_force += F * center_factor

            # 2) 슬라임 중심 이동 (Soft 상태에서도 조금씩 통째로 움직이게)
            acc_center = center_force / self.mass
            self.center_vel += acc_center * dt
            self.center_vel *= 0.98  # 중심 감쇠
            center_shift = self.center_vel * dt

            for p in self.particles:
                p.pos += center_shift

            # 3) 스프링 힘 적용
            for s in self.springs:
                s.apply(dt, temp)

            # 4) 파티클 업데이트
            for p in self.particles:
                p.update(dt, temp)
            # ============ Soft/Semi-Rigid 전용 벽 충돌 보정 ============
            radius = self.base_radius * 1.1  # 조금 여유 있게 boundary

            # 화면 크기 (상수화되어 있으면 수정)
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

            # shift가 0이 아니라면 전체 이동
            if shift.length_squared() > 0:
                self.center_pos += shift
                for p in self.particles:
                    p.pos += shift

            # 5) 🔹 형태 복원 단계 – 항상 원형으로 돌아가려는 힘
            self._shape_matching(temp)

            # Soft / Semi-Rigid는 여기서 끝
            return

        # =========================
        # RIGID-BODY (Circle + Rotation)
        # =========================
        total_force = pygame.Vector2(0, 0)
        total_torque = 0.0

        # ---- Circle vs Mouse 충돌 (슬라임 전체를 하나의 원으로 본다) ----
        delta = self.center_pos - mouse_pos
        dist = delta.length()

        radius = self.rigid_radius
        mouse_influence_radius = radius + 40  # 약간 여유 있게

        if dist < mouse_influence_radius:
            if dist == 0:
                dist = 0.01
            normal = delta / dist
            penetration = mouse_influence_radius - dist

            strength = 1500.0
            F = normal * penetration * strength
            total_force += F

            # 충돌 지점은 center에서 normal 방향으로 radius만큼 떨어진 곳으로 근사
            collision_point = self.center_pos - normal * radius
            r = collision_point - self.center_pos
            torque = r.x * F.y - r.y * F.x
            total_torque += torque

        # ---- 선형 운동 ----
        acc = total_force / self.mass
        self.center_vel += acc * dt
        self.center_vel *= 0.98  # 공기저항 같은 감쇠
        self.center_pos += self.center_vel * dt

        # 간단한 화면 경계 처리 (center 기준)
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

        # ---- 회전 운동 ----
        angular_acc = total_torque / self.inertia
        self.angular_vel += angular_acc * dt
        self.angular_vel *= 0.97  # 회전 감쇠
        self.angle += self.angular_vel * dt

        # ---- 파티클 위치 재생성 (center + 회전된 offset) ----
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
        # Soft/세미일 때만 스프링 시각화
        if not self.is_rigid:
            for s in self.springs:
                pygame.draw.line(screen, (120, 120, 200), s.p1.pos, s.p2.pos, 1)
        # 마우스 충돌 범위 시각화
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.circle(screen, (255, 100, 100), mouse_pos, 40, 1)

        
        for p in self.particles:
            p.render(screen)

class TemperatureSystem:
    def __init__(self):
        self.base_temp = 25.0
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def get_current_temperature(self):
        from math import sin, pi
        return 25 + 10 * sin(self.time * 0.5 * pi)
        # 25에다가 -10~10까지 연산 (15~35)
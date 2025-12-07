class TemperatureSystem:
    def __init__(self):
        # 시작 온도
        self.base_temp = 25.0

    def add_delta(self, delta: float):
        # 온도 변화 (예: 1키로 낮추고, 2키로 올리고)
        self.base_temp += delta
        # 너무 극단적인 값 방지
        self.base_temp = max(0.0, min(60.0, self.base_temp))

    def get_current_temperature(self) -> float:
        return self.base_temp

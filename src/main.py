import pygame
import sys
from engine.slime_engine import SlimeEngine


def temp_color(temp):
    if temp < 10:
        return (0, 150, 255)
    elif temp < 30:
        return (0, 255, 0)
    else:
        return (255, 80, 0)


def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Slime Physics Engine")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("arial", 24)
    engine = SlimeEngine(screen)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
        keys = pygame.key.get_pressed()
        if keys[pygame.K_1]:
            engine.slimes[0].temperature.add_delta(-0.2)  # 온도 내리기
        if keys[pygame.K_2]:
            engine.slimes[0].temperature.add_delta(+0.2)  # 온도 올리기

        screen.fill((25, 25, 25))

        engine.update(1 / 60)
        engine.render()

        temp = engine.slimes[0].temperature.get_current_temperature()
        text = font.render(f"Temperature: {temp:.1f}°C", True, temp_color(temp))
        screen.blit(text, (20, 20))

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()

import pygame, sys
from engine.slime_engine import SlimeEngine

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    clock = pygame.time.Clock()

    engine = SlimeEngine(screen)
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        screen.fill((25, 25, 25))
        engine.update(1/60)
        engine.render()
        
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
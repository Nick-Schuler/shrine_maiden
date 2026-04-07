import pygame
import math
import random
import json
import os

# --- Configuration ---
WIDTH, HEIGHT = 600, 800
FPS = 60
PLAYER_SPEED = 5
FOCUS_SPEED = 2
WHITE, BLACK, RED, BLUE, PINK, GOLD = (255,255,255), (0,0,0), (255,50,50), (50,50,255), (255,100,255), (255,215,0)

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(self.image, BLUE, (16, 16), 16)
        self.rect = self.image.get_rect(center=(WIDTH//2, HEIGHT - 100))
        self.hitbox_radius = 4

    def update(self, keys):
        speed = FOCUS_SPEED if keys[pygame.K_LSHIFT] else PLAYER_SPEED
        if keys[pygame.K_LEFT] and self.rect.left > 0: self.rect.x -= speed
        if keys[pygame.K_RIGHT] and self.rect.right < WIDTH: self.rect.x += speed
        if keys[pygame.K_UP] and self.rect.top > 0: self.rect.y -= speed
        if keys[pygame.K_DOWN] and self.rect.bottom < HEIGHT: self.rect.y += speed

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed, color):
        super().__init__()
        self.image = pygame.Surface((12, 12), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (6, 6), 6)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

    def update(self, *args):
        self.rect.x += self.vx
        self.rect.y += self.vy
        if not (-50 <= self.rect.x <= WIDTH + 50 and -50 <= self.rect.y <= HEIGHT + 50):
            self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((50, 50), pygame.SRCALPHA)
        pygame.draw.polygon(self.image, RED, [(25, 0), (50, 50), (0, 50)])
        self.rect = self.image.get_rect(center=(WIDTH//2, 150))
        self.timer = 0

    def update(self, *args):
        self.timer += 1
        # Hover logic
        hover_range = 200 if self.timer > 2700 else 100
        self.rect.centerx = (WIDTH // 2) + math.sin(self.timer * 0.02) * hover_range

    def fire(self, level, player, all_sprites, bullets):
        # LEVEL 1: Spiral
        if level == 1 and self.timer % 12 == 0:
            for i in range(6):
                angle = (i / 6) * 2 * math.pi + (self.timer * 0.1)
                b = Bullet(self.rect.centerx, self.rect.centery, angle, 3, PINK)
                all_sprites.add(b); bullets.add(b)

        # LEVEL 2: Rings
        elif level == 2 and self.timer % 50 == 0:
            for i in range(20):
                angle = (i / 20) * 2 * math.pi
                b = Bullet(self.rect.centerx, self.rect.centery, angle, 2.5, WHITE)
                all_sprites.add(b); bullets.add(b)

        # LEVEL 3: FIXED - Rain from Top
        elif level == 3 and self.timer % 3 == 0:
            # Angles between 0.5 and 2.5 radians point downward
            angle = random.uniform(1.2, 1.9)
            b = Bullet(random.randint(0, WIDTH), -10, angle, 5, RED)
            all_sprites.add(b); bullets.add(b)

        # LEVEL 4: Aimed Sniper
        elif level == 4 and self.timer % 40 == 0:
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            base_angle = math.atan2(dy, dx)
            for i in range(-2, 3):
                angle = base_angle + (i * 0.15)
                b = Bullet(self.rect.centerx, self.rect.centery, angle, 6, GOLD)
                all_sprites.add(b); bullets.add(b)

def load_highscore():
    try:
        if os.path.exists("danmaku_save.json"):
            with open("danmaku_save.json", "r") as f:
                return json.load(f).get("best_time", 0)
    except: pass
    return 0

def save_highscore(t):
    with open("danmaku_save.json", "w") as f:
        json.dump({"best_time": round(t, 2)}, f)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Shrine Maiden")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 20)

    all_sprites = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    player = Player()
    enemy = Enemy()
    all_sprites.add(player, enemy)

    best_time = load_highscore()
    start_ticks = pygame.time.get_ticks()
    running = True

    while running:
        clock.tick(FPS)
        current_time = (pygame.time.get_ticks() - start_ticks) / 1000

        # Level Timing
        if current_time < 15: level = 1
        elif current_time < 30: level = 2
        elif current_time < 50: level = 3
        else: level = 4

        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

        all_sprites.update(keys)
        enemy.fire(level, player, all_sprites, bullets)

        # Collision detection
        for b in bullets:
            dist = math.hypot(player.rect.centerx - b.rect.centerx, player.rect.centery - b.rect.centery)
            if dist < player.hitbox_radius + 4:
                if current_time > best_time:
                    save_highscore(current_time)
                running = False

        # Rendering
        screen.fill(BLACK)
        all_sprites.draw(screen)

        # HUD
        time_lbl = font.render(f"TIME: {round(current_time, 1)}s", True, WHITE)
        level_lbl = font.render(f"LVL: {level}", True, PINK)
        best_lbl = font.render(f"PB: {best_time}s", True, GOLD)
        screen.blit(time_lbl, (10, 10))
        screen.blit(level_lbl, (WIDTH//2 - 30, 10))
        screen.blit(best_lbl, (WIDTH - 150, 10))

        if keys[pygame.K_LSHIFT]:
            pygame.draw.circle(screen, WHITE, player.rect.center, 8, 1)
            pygame.draw.circle(screen, RED, player.rect.center, 3)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()

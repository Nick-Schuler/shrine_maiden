import pygame
import math
import random
import json
import os
import asyncio

# --- Configuration ---
WIDTH, HEIGHT = 600, 800
FPS = 60
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
RED, BLUE = (255, 50, 50), (50, 50, 255)
PINK, GOLD, GREEN = (255, 100, 255), (255, 215, 0), (0, 255, 100)

STATE_PLAYING, STATE_GAMEOVER, STATE_MENU, STATE_LEVELSELECT = 0, 1, 2, 3


# --- Optimization Cache ---
class SurfaceCache:
    """Pre-renders shapes once to save CPU on the web."""

    def __init__(self):
        self.bullets = {}
        self.player = None
        self.boss = None
        self.mob = None

    def init(self):
        # Player
        self.player = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.player, BLUE, [(20, 0), (40, 40), (20, 30), (0, 40)])

        # Mob
        self.mob = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(self.mob, (0, 255, 255), (15, 15), 15, 4)
        pygame.draw.rect(self.mob, BLACK, (13, 0, 4, 30))
        pygame.draw.rect(self.mob, BLACK, (0, 13, 30, 4))

        # Boss
        self.boss = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(self.boss, (150, 0, 0), (40, 40), 40)
        pygame.draw.circle(self.boss, RED, (40, 40), 30, 5)
        pygame.draw.rect(self.boss, GOLD, (20, 35, 40, 10))

        # Bullets
        for name, color in [("PINK", PINK), ("WHITE", WHITE), ("RED", RED), ("GOLD", GOLD), ("BLUE", BLUE),
                            ("GREEN", GREEN)]:
            s = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (7, 7), 7)
            pygame.draw.circle(s, WHITE, (7, 7), 3)
            self.bullets[name] = s

        # Large Bullet (Pink)
        lb = pygame.Surface((28, 28), pygame.SRCALPHA)
        pygame.draw.circle(lb, PINK, (14, 14), 14)
        pygame.draw.circle(lb, WHITE, (14, 14), 7)
        self.bullets["LARGE_PINK"] = lb


CACHE = SurfaceCache()


# --- Classes ---

class Starfield:
    def __init__(self):
        # Reduced star count for better performance
        self.stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(1, 3)] for _ in range(40)]

    def update(self):
        for s in self.stars:
            s[1] = (s[1] + s[2]) % HEIGHT

    def draw(self, screen):
        for s in self.stars:
            # Using set_at for single pixels is faster than drawing circles
            screen.set_at((s[0], int(s[1])), (180, 180, 180))


class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((10, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (200, 255, 255), (0, 0, 10, 24))
        self.rect = self.image.get_rect(center=(x, y))
        self.speed = 15

    def update(self):
        self.rect.y -= self.speed
        if self.rect.bottom < 0: self.kill()


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = CACHE.player
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 100))
        self.hitbox_radius_sq = 4 ** 2
        self.graze_radius_sq = 22 ** 2
        self.graze_count, self.shoot_delay = 0, 0

    def update(self, keys, all_sprites, p_bullets):
        speed = 2.0 if keys[pygame.K_LSHIFT] else 5.5
        if keys[pygame.K_LEFT] and self.rect.left > 0: self.rect.x -= speed
        if keys[pygame.K_RIGHT] and self.rect.right < WIDTH: self.rect.x += speed
        if keys[pygame.K_UP] and self.rect.top > 0: self.rect.y -= speed
        if keys[pygame.K_DOWN] and self.rect.bottom < HEIGHT: self.rect.y += speed

        if keys[pygame.K_z] and self.shoot_delay <= 0:
            b = PlayerBullet(self.rect.centerx, self.rect.top)
            all_sprites.add(b)
            p_bullets.add(b)
            self.shoot_delay = 5
        if self.shoot_delay > 0: self.shoot_delay -= 1


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed, color_name):
        super().__init__()
        self.image = CACHE.bullets.get(color_name, CACHE.bullets["PINK"])
        self.rect = self.image.get_rect(center=(x, y))
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.grazed = False

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        if not (-50 <= self.rect.x <= WIDTH + 50 and -50 <= self.rect.y <= HEIGHT + 50):
            self.kill()


class Mob(pygame.sprite.Sprite):
    def __init__(self, x, y, path_type):
        super().__init__()
        self.image = CACHE.mob
        self.rect = self.image.get_rect(center=(x, y))
        self.hp = 8
        self.timer = 0
        self.path_type = path_type

    def update(self):
        self.timer += 1
        if self.path_type == "sin":
            self.rect.x += 2.5
            self.rect.y = 120 + math.sin(self.timer * 0.04) * 60
        elif self.path_type == "dive":
            self.rect.y += 3.5
        if self.rect.top > HEIGHT or self.rect.left > WIDTH or self.rect.right < 0: self.kill()


class Enemy(pygame.sprite.Sprite):
    def __init__(self, is_boss=True):
        super().__init__()
        self.is_boss = is_boss
        self.image = CACHE.boss
        self.rect = self.image.get_rect(center=(WIDTH // 2, 150))
        self.hp = 150
        self.max_hp = 150
        self.timer = 0
        self.invuln_timer = 0
        self.flash_timer = 0

    def take_damage(self, amt):
        if self.invuln_timer <= 0:
            self.hp -= amt
            self.flash_timer = 4
            return True
        return False

    def update(self):
        self.timer += 1
        if self.invuln_timer > 0: self.invuln_timer -= 1
        if self.is_boss:
            bx = (WIDTH // 2) + math.sin(self.timer * 0.02) * 150
            by = 150 + math.cos(self.timer * 0.03) * 40
            self.rect.center = (bx, by)

    def fire(self, level, player, all_sprites, bullets):
        if self.invuln_timer > 0: return
        t, cx, cy = self.timer, self.rect.centerx, self.rect.centery

        # Pattern logic (same as before, but passing color names)
        if level == 1 and t % 20 == 0:
            for i in range(6):
                b = Bullet(cx, cy, (t * 0.08) + (i * math.pi / 3), 3, "PINK")
                all_sprites.add(b);
                bullets.add(b)
        elif level == 2 and t % 50 == 0:
            for i in range(16):
                b = Bullet(cx, cy, i * math.pi / 8, 2.5, "WHITE")
                all_sprites.add(b);
                bullets.add(b)
        elif level == 3 and t % 12 == 0:
            off = math.sin(t * 0.04) * 0.8
            for a in [math.pi / 2 + off, math.pi / 2 - off]:
                b = Bullet(cx, cy, a, 4.5, "RED")
                all_sprites.add(b);
                bullets.add(b)
        elif level >= 10 and t % 7 == 0:
            b1 = Bullet(cx, cy, t * 0.09, 3.5, "RED")
            b2 = Bullet(cx, cy, -t * 0.09, 3.5, "BLUE")
            all_sprites.add(b1, b2);
            bullets.add(b1, b2)


# --- Main Game ---

async def main():
    pygame.init()
    CACHE.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    f_sub = pygame.font.SysFont("monospace", 18)
    f_btn = pygame.font.SysFont("monospace", 22, True)
    f_main = pygame.font.SysFont("Arial", 48, True)

    def reset_game(lvl=1):
        all_sprites, e_bullets, p_bullets, enemies = pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group()
        p = Player()
        b = Enemy(True)
        b.hp = 150 + (lvl * 70);
        b.max_hp = b.hp
        all_sprites.add(p, b);
        enemies.add(b)
        return all_sprites, e_bullets, p_bullets, enemies, p, b, lvl

    starfield = Starfield()
    all_sprites, e_bullets, p_bullets, enemies, player, boss, level = reset_game()
    game_state = STATE_MENU

    while True:
        mouse_pos, mouse_click = pygame.mouse.get_pos(), False
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return
            if event.type == pygame.MOUSEBUTTONDOWN: mouse_click = True

        keys = pygame.key.get_pressed()

        if game_state == STATE_MENU:
            screen.fill(BLACK)
            starfield.draw(screen)
            txt = f_main.render("SHRINE MAIDEN", True, WHITE)
            screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 150))
            p_rect = pygame.Rect(WIDTH // 2 - 100, 300, 200, 50)
            hover = p_rect.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (0, 150, 0) if hover else (0, 80, 0), p_rect, border_radius=8)
            msg = f_btn.render("PLAY", True, WHITE)
            screen.blit(msg, (p_rect.centerx - msg.get_width() // 2, p_rect.centery - msg.get_height() // 2))
            if hover and mouse_click: game_state = STATE_PLAYING

        elif game_state == STATE_PLAYING:
            starfield.update()
            player.update(keys, all_sprites, p_bullets)

            if random.random() < 0.008:
                side = random.choice([-50, WIDTH + 50])
                m = Mob(side, 120, "sin" if side < 0 else "dive")
                all_sprites.add(m);
                enemies.add(m)

            for e in enemies:
                e.update()
                if hasattr(e, 'fire'): e.fire(level, player, all_sprites, e_bullets)

            p_bullets.update()
            e_bullets.update()

            # Optimized Collision (Squared Distance)
            px, py = player.rect.center
            for b in e_bullets:
                dx, dy = px - b.rect.centerx, py - b.rect.centery
                dist_sq = dx * dx + dy * dy
                if dist_sq < 45:  # Hit (approx 6.7 pixels)
                    game_state = STATE_GAMEOVER
                elif dist_sq < 484 and not b.grazed:  # Graze (22 pixels)
                    player.graze_count += 1;
                    b.grazed = True

            for p_b in p_bullets:
                hits = pygame.sprite.spritecollide(p_b, enemies, False)
                for e in hits:
                    p_b.kill()
                    if e.take_damage(2) and e.hp <= 0:
                        if e == boss:
                            level += 1;
                            boss.invuln_timer = 120
                            boss.hp = 150 + (level * 70);
                            boss.max_hp = boss.hp
                            for bullet in e_bullets: bullet.kill()
                        else:
                            e.kill()

            screen.fill(BLACK)
            starfield.draw(screen)
            all_sprites.draw(screen)

            # UI
            pygame.draw.rect(screen, (40, 40, 40), (100, 20, 400, 15))
            pygame.draw.rect(screen, GREEN, (100, 20, int(400 * (max(0, boss.hp) / boss.max_hp)), 15))
            screen.blit(f_sub.render(f"PHASE {level} | GRAZE {player.graze_count}", True, PINK), (100, 40))

        elif game_state == STATE_GAMEOVER:
            txt = f_main.render("FAILED", True, RED)
            screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2))
            if mouse_click:
                all_sprites, e_bullets, p_bullets, enemies, player, boss, level = reset_game(1)
                game_state = STATE_MENU

        pygame.display.flip()
        await asyncio.sleep(0)  # Critical for browser performance


if __name__ == "__main__":
    asyncio.run(main())

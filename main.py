import pygame
import math
import random
import asyncio

# --- Configuration ---
WIDTH, HEIGHT = 600, 800
FPS = 60
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
RED, BLUE = (255, 50, 50), (50, 50, 255)
PINK, GOLD, GREEN = (255, 100, 255), (255, 215, 0), (0, 255, 100)

STATE_PLAYING, STATE_GAMEOVER, STATE_MENU = 0, 1, 2


# --- Optimization Cache ---
class SurfaceCache:
    def __init__(self):
        self.bullets = {}
        self.player = None
        self.boss = None
        self.mob = None

    def init(self):
        self.player = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.player, BLUE, [(20, 0), (40, 40), (20, 30), (0, 40)])

        self.mob = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(self.mob, (0, 255, 255), (15, 15), 15, 4)
        pygame.draw.rect(self.mob, BLACK, (13, 0, 4, 30))
        pygame.draw.rect(self.mob, BLACK, (0, 13, 30, 4))

        self.boss = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(self.boss, (150, 0, 0), (40, 40), 40)
        pygame.draw.circle(self.boss, RED, (40, 40), 30, 5)
        pygame.draw.rect(self.boss, GOLD, (20, 35, 40, 10))

        for name, color in [("PINK", PINK), ("WHITE", WHITE), ("RED", RED), ("GOLD", GOLD), ("BLUE", BLUE),
                            ("GREEN", GREEN)]:
            s = pygame.Surface((14, 14), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (7, 7), 7)
            pygame.draw.circle(s, WHITE, (7, 7), 3)
            self.bullets[name] = s


CACHE = SurfaceCache()


# --- Classes ---

class Starfield:
    def __init__(self):
        self.stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(100, 300)] for _ in
                      range(40)]

    def update(self, dt):
        for s in self.stars:
            s[1] += s[2] * dt
            if s[1] > HEIGHT:
                s[1] = 0
                s[0] = random.randint(0, WIDTH)

    def draw(self, screen):
        for s in self.stars:
            screen.set_at((s[0], int(s[1])), (180, 180, 180))


class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((10, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (200, 255, 255), (0, 0, 10, 24))
        self.rect = self.image.get_rect(center=(x, y))
        self.pos_y = float(self.rect.y)
        self.speed = 900  # Pixels per second

    def update(self, dt):
        self.pos_y -= self.speed * dt
        self.rect.y = int(self.pos_y)
        if self.rect.bottom < 0: self.kill()


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = CACHE.player
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 100))
        self.pos = pygame.Vector2(self.rect.center)
        self.graze_count, self.shoot_delay = 0, 0

    def update(self, keys, dt, all_sprites, p_bullets):
        speed = 150.0 if keys[pygame.K_LSHIFT] else 350.0
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_LEFT]: move.x -= 1
        if keys[pygame.K_RIGHT]: move.x += 1
        if keys[pygame.K_UP]: move.y -= 1
        if keys[pygame.K_DOWN]: move.y += 1

        if move.length_squared() > 0:
            self.pos += move.normalize() * speed * dt

        # Bounds checking
        self.pos.x = max(20, min(WIDTH - 20, self.pos.x))
        self.pos.y = max(20, min(HEIGHT - 20, self.pos.y))
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        if keys[pygame.K_z] and self.shoot_delay <= 0:
            b = PlayerBullet(self.rect.centerx, self.rect.top)
            all_sprites.add(b)
            p_bullets.add(b)
            self.shoot_delay = 0.08  # Seconds between shots
        if self.shoot_delay > 0: self.shoot_delay -= dt


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed, color_name):
        super().__init__()
        self.image = CACHE.bullets.get(color_name, CACHE.bullets["PINK"])
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
        self.grazed = False

    def update(self, dt):
        self.pos += self.vel * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        if not (-50 <= self.pos.x <= WIDTH + 50 and -50 <= self.pos.y <= HEIGHT + 50):
            self.kill()


class Mob(pygame.sprite.Sprite):
    def __init__(self, x, y, path_type):
        super().__init__()
        self.image = CACHE.mob
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(x, y)
        self.hp = 8
        self.timer = 0
        self.path_type = path_type

    def update(self, dt):
        self.timer += dt
        if self.path_type == "sin":
            self.pos.x += 150 * dt
            self.pos.y = 120 + math.sin(self.timer * 3.0) * 60
        elif self.path_type == "dive":
            self.pos.y += 200 * dt
        self.rect.center = (int(self.pos.x), int(self.pos.y))
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

    def take_damage(self, amt):
        if self.invuln_timer <= 0:
            self.hp -= amt
            return True
        return False

    def update(self, dt):
        self.timer += dt
        if self.invuln_timer > 0: self.invuln_timer -= dt
        if self.is_boss:
            bx = (WIDTH // 2) + math.sin(self.timer * 1.2) * 150
            by = 150 + math.cos(self.timer * 1.8) * 40
            self.rect.center = (int(bx), int(by))

    def fire(self, level, dt, all_sprites, bullets):
        if self.invuln_timer > 0: return
        cx, cy = self.rect.center

        # Fire rate controlled by modulated timers
        if level == 1 and int(self.timer * 60) % 20 == 0:
            for i in range(6):
                b = Bullet(cx, cy, (self.timer * 4) + (i * math.pi / 3), 180, "PINK")
                all_sprites.add(b);
                bullets.add(b)
        elif level == 2 and int(self.timer * 60) % 50 == 0:
            for i in range(16):
                b = Bullet(cx, cy, i * math.pi / 8, 150, "WHITE")
                all_sprites.add(b);
                bullets.add(b)
        elif level >= 3 and int(self.timer * 60) % 12 == 0:
            off = math.sin(self.timer * 2.4) * 0.8
            for a in [math.pi / 2 + off, math.pi / 2 - off]:
                b = Bullet(cx, cy, a, 270, "RED")
                all_sprites.add(b);
                bullets.add(b)


# --- Main Game ---

async def main():
    pygame.init()
    CACHE.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    f_sub = pygame.font.SysFont("monospace", 18)
    f_btn = pygame.font.SysFont("monospace", 22, True)
    f_main = pygame.font.SysFont("Arial", 48, True)

    def reset_game(lvl=1):
        all_sprites = pygame.sprite.Group()
        e_bullets = pygame.sprite.Group()
        p_bullets = pygame.sprite.Group()
        enemies = pygame.sprite.Group()
        p = Player()
        b = Enemy(True)
        b.hp = 150 + (lvl * 70)
        b.max_hp = b.hp
        all_sprites.add(p, b)
        enemies.add(b)
        return all_sprites, e_bullets, p_bullets, enemies, p, b, lvl

    starfield = Starfield()
    all_sprites, e_bullets, p_bullets, enemies, player, boss, level = reset_game()
    game_state = STATE_MENU

    while True:
        # 1. Delta Time Calculation
        dt = clock.tick(FPS) / 1000.0
        if dt > 0.1: dt = 0.016  # Prevent huge jumps if window is dragged

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
            starfield.update(dt)
            player.update(keys, dt, all_sprites, p_bullets)

            if random.random() < 0.5 * dt:  # Frequency adjusted for time
                side = random.choice([-50, WIDTH + 50])
                m = Mob(side, 120, "sin" if side < 0 else "dive")
                all_sprites.add(m);
                enemies.add(m)

            for e in enemies:
                e.update(dt)
                if hasattr(e, 'fire'): e.fire(level, dt, all_sprites, e_bullets)

            p_bullets.update(dt)
            e_bullets.update(dt)

            # Collision
            px, py = player.rect.center
            for b in e_bullets:
                dx, dy = px - b.rect.centerx, py - b.rect.centery
                dist_sq = dx * dx + dy * dy
                if dist_sq < 36:  # Hitbox
                    game_state = STATE_GAMEOVER
                elif dist_sq < 484 and not b.grazed:  # Graze
                    player.graze_count += 1
                    b.grazed = True

            for p_b in p_bullets:
                hits = pygame.sprite.spritecollide(p_b, enemies, False)
                for e in hits:
                    p_b.kill()
                    if e.take_damage(2) and e.hp <= 0:
                        if e == boss:
                            level += 1
                            boss.invuln_timer = 2.0
                            boss.hp = 150 + (level * 70)
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
        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())

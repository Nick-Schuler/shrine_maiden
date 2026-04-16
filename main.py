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


# --- Classes ---

class Starfield:
    def __init__(self):
        self.stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT), random.choice([1, 2, 4])] for _ in
                      range(95)]

    def update(self):
        for s in self.stars:
            s[1] = (s[1] + s[2]) % HEIGHT

    def draw(self, screen):
        for s in self.stars:
            color = (130, 130, 130) if s[2] < 3 else (200, 200, 200)
            pygame.draw.circle(screen, color, (s[0], s[1]), s[2] // 2 + 1)


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
        self.image = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.image, BLUE, [(20, 0), (40, 40), (20, 30), (0, 40)])
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 100))
        self.hitbox_radius, self.graze_radius = 4, 22
        self.graze_count, self.shoot_delay = 0, 0

    def update(self, keys, all_sprites, p_bullets):
        speed = 2.0 if keys[pygame.K_LSHIFT] else 5.5
        if keys[pygame.K_LEFT] and self.rect.left > 0: self.rect.x -= speed
        if keys[pygame.K_RIGHT] and self.rect.right < WIDTH: self.rect.x += speed
        if keys[pygame.K_UP] and self.rect.top > 0: self.rect.y -= speed
        if keys[pygame.K_DOWN] and self.rect.bottom < HEIGHT: self.rect.y += speed

        if keys[pygame.K_z] and self.shoot_delay <= 0:
            b = PlayerBullet(self.rect.centerx, self.rect.top)
            all_sprites.add(b);
            p_bullets.add(b)
            self.shoot_delay = 5
        if self.shoot_delay > 0: self.shoot_delay -= 1


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, speed, color, size=14):
        super().__init__()
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (size // 2, size // 2), size // 2)
        pygame.draw.circle(self.image, WHITE, (size // 2, size // 2), size // 4)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed
        self.grazed = False

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        if not (-100 <= self.rect.x <= WIDTH + 100 and -100 <= self.rect.y <= HEIGHT + 100):
            self.kill()


class Mob(pygame.sprite.Sprite):
    def __init__(self, x, y, path_type):
        super().__init__()
        self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
        # Unique look for small mobs: segmented cyan circle
        pygame.draw.circle(self.image, (0, 255, 255), (15, 15), 15, 4)
        pygame.draw.rect(self.image, BLACK, (13, 0, 4, 30))  # Vertical segment
        pygame.draw.rect(self.image, BLACK, (0, 13, 30, 4))  # Horizontal segment

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
        self.size = 80 if is_boss else 40
        self.base_image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)

        # --- RESTORED BOSS VISUAL DESIGN ---
        if is_boss:
            # Dark red base/center
            pygame.draw.circle(self.base_image, (150, 0, 0), (40, 40), 40)
            # Bright red outer rings
            pygame.draw.circle(self.base_image, RED, (40, 40), 30, 5)
            # Gold horizontal bar
            pygame.draw.rect(self.base_image, GOLD, (20, 35, 40, 10))
        else:
            # Small enemy look (different from mobs)
            pygame.draw.circle(self.base_image, (200, 100, 0), (20, 20), 20)
            pygame.draw.circle(self.base_image, GOLD, (20, 20), 10, 3)

        self.image = self.base_image.copy()
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

        if self.flash_timer > 0:
            self.flash_timer -= 1
            self.image.fill(WHITE, special_flags=pygame.BLEND_RGB_ADD)
        else:
            self.image = self.base_image.copy()
            if self.invuln_timer > 0: self.image.set_alpha(120)

    def fire(self, level, player, all_sprites, bullets):
        if self.invuln_timer > 0: return
        t = self.timer
        cx, cy = self.rect.center

        if level == 1:
            if t % 20 == 0:
                for i in range(6):
                    b = Bullet(cx, cy, (t * 0.08) + (i * math.pi / 3), 3, PINK)
                    all_sprites.add(b);
                    bullets.add(b)
        elif level == 2:
            if t % 50 == 0:
                for i in range(16):
                    b = Bullet(cx, cy, i * math.pi / 8, 2.5, WHITE)
                    all_sprites.add(b);
                    bullets.add(b)
        elif level == 3:
            if t % 12 == 0:
                off = math.sin(t * 0.04) * 0.8
                for a in [math.pi / 2 + off, math.pi / 2 - off]:
                    b = Bullet(cx, cy, a, 4.5, RED)
                    all_sprites.add(b);
                    bullets.add(b)
        elif level == 4:
            if t % 15 == 0:
                for i in range(4):
                    b = Bullet(cx, cy, (t * -0.08) + (i * math.pi / 2), 3.5, GOLD)
                    all_sprites.add(b);
                    bullets.add(b)
        elif level == 5:
            if t % 25 == 0:
                for i in range(10):
                    b = Bullet(cx, cy, i * math.pi / 5 + t * 0.02, 2.5 + math.sin(i), BLUE)
                    all_sprites.add(b);
                    bullets.add(b)
        elif level == 6:
            if t % 6 == 0:
                b = Bullet(cx, cy, t * 0.12, 3.2, WHITE)
                all_sprites.add(b);
                bullets.add(b)
        elif level == 7:  # Gravity Linger
            if t % 40 == 0:
                for i in range(18):
                    b = Bullet(cx, cy, i * math.pi / 9, 1.2 + (i % 2), GOLD)
                    all_sprites.add(b);
                    bullets.add(b)
        elif level == 8:  # Geometry
            if t % 30 == 0:
                for i in range(4):
                    for j in range(4):
                        ang = (i * math.pi / 2) + (j * 0.15)
                        b = Bullet(cx, cy, ang, 3.8, GREEN)
                        all_sprites.add(b);
                        bullets.add(b)
        elif level == 9:  # Homing Bubbles
            if t % 80 == 0:
                dx, dy = player.rect.centerx - cx, player.rect.centery - cy
                b = Bullet(cx, cy, math.atan2(dy, dx), 1.8, PINK, 28)
                all_sprites.add(b);
                bullets.add(b)
        elif level >= 10:  # Final Curtain
            if t % 7 == 0:
                b1 = Bullet(cx, cy, t * 0.09, 3.5, RED)
                b2 = Bullet(cx, cy, -t * 0.09, 3.5, BLUE)
                all_sprites.add(b1, b2);
                bullets.add(b1, b2)


# --- Data Handling ---
def load_data():
    if os.path.exists("save.json"):
        with open("save.json", "r") as f: return json.load(f)
    return {"max_phase": 1, "test_mode": False}


def save_data(phase):
    data = load_data()
    if phase > data["max_phase"]:
        data["max_phase"] = phase
        with open("save.json", "w") as f: json.dump(data, f)


# --- Main Game ---

async def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    f_sub, f_btn, f_main = pygame.font.SysFont("monospace", 18), pygame.font.SysFont("monospace", 22,
                                                                                     True), pygame.font.SysFont("Arial",
                                                                                                                48,
                                                                                                                True)

    def reset_game(lvl=1):
        all_sprites, e_bullets, p_bullets, enemies = pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group()
        p = Player();
        b = Enemy(True)
        b.hp = 150 + (lvl * 70);
        b.max_hp = b.hp
        all_sprites.add(p, b);
        enemies.add(b)
        return all_sprites, e_bullets, p_bullets, enemies, p, b, lvl

    starfield = Starfield()
    all_sprites, e_bullets, p_bullets, enemies, player, boss, level = reset_game()
    game_state, persistent_data = STATE_MENU, load_data()

    while True:
        # DT calculation and FPS capping
        # dt = clock.tick(FPS)

        mouse_pos, mouse_click = pygame.mouse.get_pos(), False
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); return
            if event.type == pygame.MOUSEBUTTONDOWN: mouse_click = True

        keys = pygame.key.get_pressed()

        if game_state == STATE_MENU:
            screen.fill(BLACK);
            starfield.update();
            starfield.draw(screen)
            txt = f_main.render("SHRINE MAIDEN", True, WHITE)
            screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 150))

            p_rect, l_rect = pygame.Rect(WIDTH // 2 - 100, 300, 200, 50), pygame.Rect(WIDTH // 2 - 100, 370, 200, 50)

            for r, t, s in [(p_rect, "PLAY", STATE_PLAYING), (l_rect, "LEVELS", STATE_LEVELSELECT)]:
                hover = r.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (0, 150, 0) if hover else (0, 80, 0), r, border_radius=8)
                msg = f_btn.render(t, True, WHITE)
                screen.blit(msg, (r.centerx - msg.get_width() // 2, r.centery - msg.get_height() // 2))
                if hover and mouse_click:
                    if s == STATE_PLAYING:
                        all_sprites, e_bullets, p_bullets, enemies, player, boss, level = reset_game(1)
                    game_state = s

        elif game_state == STATE_LEVELSELECT:
            screen.fill(BLACK);
            starfield.draw(screen)
            persistent_data = load_data()
            max_p = 10 if persistent_data.get("test_mode") else persistent_data["max_phase"]

            for i in range(1, max_p + 1):
                r = pygame.Rect(WIDTH // 2 - 140 + ((i - 1) % 3) * 100, 200 + ((i - 1) // 3) * 60, 80, 40)
                hover = r.collidepoint(mouse_pos)
                pygame.draw.rect(screen, (100, 100, 100) if hover else (50, 50, 50), r)
                screen.blit(f_sub.render(f"P{i}", True, WHITE), (r.centerx - 10, r.centery - 10))
                if hover and mouse_click:
                    all_sprites, e_bullets, p_bullets, enemies, player, boss, level = reset_game(i)
                    game_state = STATE_PLAYING

            b_rect = pygame.Rect(WIDTH // 2 - 50, HEIGHT - 100, 100, 40)
            if b_rect.collidepoint(mouse_pos) and mouse_click: game_state = STATE_MENU
            pygame.draw.rect(screen, RED, b_rect);
            screen.blit(f_sub.render("BACK", True, WHITE), (b_rect.x + 25, b_rect.y + 10))

        elif game_state == STATE_PLAYING:
            starfield.update();
            player.update(keys, all_sprites, p_bullets)

            # Managed mob spawning
            if level > 3 and random.random() < 0.008:
                side = random.choice([-50, WIDTH + 50])
                m = Mob(side, 120, "sin" if side < 0 else "dive")
                all_sprites.add(m);
                enemies.add(m)

            for e in enemies:
                e.update()
                if hasattr(e, 'fire'): e.fire(level, player, all_sprites, e_bullets)

            p_bullets.update();
            e_bullets.update()

            # Collisions
            for p_b in p_bullets:
                hits = pygame.sprite.spritecollide(p_b, enemies, False)
                for e in hits:
                    p_b.kill()
                    if e.take_damage(2) and e.hp <= 0:
                        if e == boss:
                            level += 1;
                            save_data(level)
                            boss.invuln_timer = 120
                            boss.hp = 150 + (level * 70);
                            boss.max_hp = boss.hp
                            for bullet in e_bullets: bullet.kill()
                        else:
                            e.kill()

            for b in e_bullets:
                d = math.hypot(player.rect.centerx - b.rect.centerx, player.rect.centery - b.rect.centery)
                if d < player.hitbox_radius + 4:
                    game_state = STATE_GAMEOVER
                elif d < player.graze_radius and not b.grazed:
                    player.graze_count += 1;
                    b.grazed = True

            screen.fill(BLACK);
            starfield.draw(screen);
            all_sprites.draw(screen)

            # Boss HP bar UI
            pygame.draw.rect(screen, (40, 40, 40), (100, 20, 400, 15))
            pygame.draw.rect(screen, GREEN, (100, 20, 400 * (max(0, boss.hp) / boss.max_hp), 15))
            screen.blit(f_sub.render(f"PHASE {level} | GRAZE {player.graze_count}", True, PINK), (100, 40))
            if keys[pygame.K_LSHIFT]:
                pygame.draw.circle(screen, WHITE, player.rect.center, 10, 1)
                pygame.draw.circle(screen, RED, player.rect.center, 3)

        elif game_state == STATE_GAMEOVER:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA);
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            txt = f_main.render("MISSION FAILED", True, RED)
            screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 - 50))
            if mouse_click: game_state = STATE_MENU

        pygame.display.flip()
        await asyncio.sleep(0.01)


if __name__ == "__main__":
    asyncio.run(main())

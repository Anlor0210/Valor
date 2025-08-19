import random, sys, pygame
from config import *
from map import (
    build_static_map,
    build_grid,
    pos_to_cell,
    cell_center,
    nearest_passable_cell,
    has_line_of_sight,
)
from entities import Agent, Bullet, BombState
from ai import bot_ai, sees
from render import load_sprites, draw_bomb

pygame.init()
pygame.display.set_caption("Valor 4v4 BombMode")
screen=pygame.display.set_mode((VIEW_W, VIEW_H))
clock=pygame.time.Clock()
font=pygame.font.SysFont("consolas",18)
big_font=pygame.font.SysFont("consolas",40,bold=True)
sprites = load_sprites()


def clamp(value, min_value, max_value):
    """Return *value* limited to the inclusive range [min_value, max_value]."""
    return max(min_value, min(max_value, value))

def random_zone(grid):
    radius=random.randint(BOMB_RADIUS_MIN,BOMB_RADIUS_MAX)
    while True:
        c=random.randrange(COLS); r=random.randrange(ROWS)
        good=True
        for dx in range(-radius,radius+1):
            for dy in range(-radius,radius+1):
                if dx*dx+dy*dy>radius*radius: continue
                x=c+dx; y=r+dy
                if x<0 or y<0 or x>=COLS or y>=ROWS or not grid[x][y]:
                    good=False; break
            if not good: break
        if good:
            return cell_center(c,r), radius

def _make_nav():
    return {"path": None, "goal": None, "idx": 0, "last_compute": 0}

def _get_nav(navs, agent):
    # ensure a nav entry exists for this agent object
    if agent not in navs:
        navs[agent] = _make_nav()
    return navs[agent]

def reset_round():
    walls=build_static_map()
    grid=build_grid(walls)
    zone_center, radius = random_zone(grid)
    bomb=BombState(zone_center, radius)
    player_team=random.choice(["ATT","DEF"])
    att_spawns=[(200,HEIGHT-200),(260,HEIGHT-260),(320,HEIGHT-320),(380,HEIGHT-380)]
    def_spawns=[(WIDTH-200,200),(WIDTH-260,260),(WIDTH-320,320),(WIDTH-380,380)]
    attackers=[]; defenders=[]
    if player_team=="ATT":
        attackers.append(Agent(*att_spawns[0], BLUE, "ATT", True, "YOU"))
        for i in range(1,4): attackers.append(Agent(*att_spawns[i], BLUE_BOT, "ATT", name=f"ALLY-{i}"))
        for i in range(4): defenders.append(Agent(*def_spawns[i], RED_BOT if i else RED, "DEF", name=f"ENEMY-{i+1}"))
    else:
        defenders.append(Agent(*def_spawns[0], RED, "DEF", True, "YOU"))
        for i in range(1,4): defenders.append(Agent(*def_spawns[i], RED_BOT, "DEF", name=f"ALLY-{i}"))
        for i in range(4): attackers.append(Agent(*att_spawns[i], BLUE_BOT if i else BLUE, "ATT", name=f"ENEMY-{i+1}"))
    navs = {a: _make_nav() for a in attackers[1:] + defenders}
    return walls,grid,bomb,attackers,defenders,navs

def alive(lst): return [a for a in lst if a.alive]
def active_or_downed(lst): return [a for a in lst if (a.alive or a.downed)]

def main():
    walls,grid,bomb,attackers,defenders,navs = reset_round()
    bullets=[]
    round_over=False; winner_text=""
    running=True

    def draw_minimap(player):
        scale = MINIMAP_SIZE / WIDTH
        mini = pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE), pygame.SRCALPHA)
        mini.fill((20,20,24))
        for w in walls:
            pygame.draw.rect(mini, (100,100,100), pygame.Rect(int(w.x*scale), int(w.y*scale), int(w.w*scale), int(w.h*scale)))
        pygame.draw.circle(mini, (80,80,120), (int(bomb.zone_center[0]*scale), int(bomb.zone_center[1]*scale)), int(bomb.radius*GRID*scale),1)
        now = pygame.time.get_ticks()
        for ag in attackers + defenders:
            if ag.team == player.team:
                pygame.draw.circle(mini, ag.color, (int(ag.x*scale), int(ag.y*scale)), 3)
            else:
                seen_time = ag.seen_by_att if player.team=='ATT' else ag.seen_by_def
                elapsed = now - seen_time
                if elapsed < ENEMY_MEMORY_MS:
                    alpha = max(50, 255 - int(255*elapsed/ENEMY_MEMORY_MS))
                    dot = pygame.Surface((6,6), pygame.SRCALPHA)
                    pygame.draw.circle(dot, (*ag.color, alpha), (3,3), 3)
                    mini.blit(dot, (int(ag.x*scale)-3, int(ag.y*scale)-3))
        screen.blit(mini, (VIEW_W - MINIMAP_SIZE - 20,20))
    while running:
        dt=clock.tick(FPS)
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                running=False
            if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                running=False
            if event.type==pygame.KEYDOWN and event.key==pygame.K_F5:
                walls,grid,bomb,attackers,defenders,navs = reset_round()
                bullets=[]; round_over=False; winner_text=""

        keys=pygame.key.get_pressed()
        player=[a for a in attackers+defenders if a.is_player][0]
        now=pygame.time.get_ticks()
        player.move_player(keys, walls)

        mx,my=pygame.mouse.get_pos()
        world_mouse=(mx + clamp(player.x-VIEW_W//2,0,WIDTH-VIEW_W), my + clamp(player.y-VIEW_H//2,0,HEIGHT-VIEW_H))
        if pygame.mouse.get_pressed()[0]:
            player.shoot(world_mouse, now, bullets)

        # Player revive/plant/defuse
        if keys[pygame.K_r]:
            friends = attackers if player.team=="ATT" else defenders
            nearest=None; best=1e9
            for fr in friends:
                if fr.downed:
                    d=(player.x-fr.x)**2+(player.y-fr.y)**2
                    if d<best:
                        best=d; nearest=fr
            if nearest and math.hypot(player.x-nearest.x, player.y-nearest.y)<=REVIVE_RANGE:
                if player.lock_reason is None:
                    player.lock_reason='revive'; player.lock_start=now; player.reviving_target=nearest; nearest.pause_bleedout()
                elif player.lock_reason=='revive' and player.reviving_target is nearest:
                    if now-player.lock_start>=REVIVE_MS:
                        nearest.revive(); nearest.resume_bleedout(); player.lock_reason=None; player.reviving_target=None
            else:
                if player.lock_reason=='revive' and player.reviving_target:
                    player.reviving_target.resume_bleedout()
                    player.lock_reason=None; player.reviving_target=None
        else:
            if player.lock_reason=='revive' and player.reviving_target:
                player.reviving_target.resume_bleedout(); player.lock_reason=None; player.reviving_target=None
        if keys[pygame.K_4]:
            if bomb.state=='idle' and player.team=='ATT' and bomb.in_zone(player.pos):
                if player.lock_reason is None:
                    player.lock_reason='plant'; player.lock_start=now
                if now-player.lock_start>=PLANT_HOLD_MS:
                    bomb.commit_plant(player.team); player.lock_reason=None
            elif bomb.state=='planted' and player.team=='DEF' and bomb.in_zone(player.pos):
                if player.lock_reason is None:
                    player.lock_reason='defuse'; player.lock_start=now
                if now-player.lock_start>=DEFUSE_HOLD_MS:
                    bomb.commit_defuse(); player.lock_reason=None
        else:
            if player.lock_reason in ('plant','defuse'):
                player.lock_reason=None

        # Bots
        for a in attackers[1:] if player.team=='ATT' else attackers:
            if not a.is_player:
                bot_ai(a, defenders, attackers, walls, bullets, grid, _get_nav(navs, a), bomb)
        for d in defenders[1:] if player.team=='DEF' else defenders:
            if not d.is_player:
                bot_ai(d, attackers, defenders, walls, bullets, grid, _get_nav(navs, d), bomb)

        for b in bullets:
            b.update(walls)
            if b.dead: continue
            targets = defenders if b.team=='ATT' else attackers
            for t in targets:
                if (t.alive or t.downed) and pygame.Vector2(b.x,b.y).distance_to(t.pos) <= RADIUS+BULLET_RADIUS:
                    if t.alive: t.take_damage(BULLET_DAMAGE)
                    b.dead=True; break
        bullets=[b for b in bullets if not b.dead]

        now_tick = pygame.time.get_ticks()
        for a in attackers:
            for d in defenders:
                if sees(a, d, walls):
                    d.seen_by_att = now_tick
                if sees(d, a, walls):
                    a.seen_by_def = now_tick

        tick = now_tick
        for ag in attackers + defenders:
            if ag.downed and tick - ag.downed_at - ag.bleed_paused >= DOWNED_TIMEOUT_MS:
                ag.downed=False; ag.alive=False; ag.hp=0; ag.reviving_target=None
                ag.bleed_paused=0; ag.bleed_paused_start=None

        if bomb.state=='planted' and pygame.time.get_ticks()-bomb.planted_time >= BOMB_TIMER_MS:
            bomb.state='exploded'

        A_active=len(active_or_downed(attackers))
        D_active=len(active_or_downed(defenders))
        A_alive=len(alive(attackers))
        D_alive=len(alive(defenders))

        if bomb.state=='idle':
            if A_alive==0 and all(not a.downed for a in attackers):
                winner_text="DEFENDERS WIN — Attackers eliminated"; round_over=True
            elif D_alive==0 and all(not d.downed for d in defenders):
                winner_text="ATTACKERS WIN — Defenders eliminated"; round_over=True
        elif bomb.state=='planted':
            if D_alive==0 and all(not d.downed for d in defenders):
                winner_text="ATTACKERS WIN — All defenders down"; round_over=True
            elif bomb.state=='exploded':
                winner_text="ATTACKERS WIN — Bomb exploded"; round_over=True
            elif bomb.state=='defused':
                winner_text="DEFENDERS WIN — Bomb defused"; round_over=True

        cam_x = clamp(player.x - VIEW_W//2, 0, WIDTH - VIEW_W)
        cam_y = clamp(player.y - VIEW_H//2, 0, HEIGHT - VIEW_H)

        screen.fill(GRID_DARK)
        for x in range(0, WIDTH, 48):
            if cam_x <= x <= cam_x+VIEW_W:
                pygame.draw.line(screen, GRID_LINE, (x-cam_x,0), (x-cam_x,VIEW_H))
        for y in range(0, HEIGHT, 48):
            if cam_y <= y <= cam_y+VIEW_H:
                pygame.draw.line(screen, GRID_LINE, (0,y-cam_y), (VIEW_W,y-cam_y))
        for rect in walls:
            pygame.draw.rect(screen, WALL_DARK, rect.move(-cam_x,-cam_y))
            pygame.draw.rect(screen, WALL_EDGE, rect.move(-cam_x,-cam_y),2)
        pygame.draw.circle(screen,(60,60,60),(bomb.zone_center[0]-cam_x,bomb.zone_center[1]-cam_y),bomb.radius*GRID,2)
        draw_bomb(screen, bomb, sprites, (cam_x, cam_y))

        for a in attackers:
            a.draw(screen,(cam_x,cam_y),font)
        for d in defenders:
            d.draw(screen,(cam_x,cam_y),font)
        for b in bullets:
            b.draw(screen,(cam_x,cam_y))

        def bar(x,y,w,h,frac,col):
            pygame.draw.rect(screen,(40,40,40),(x,y,w,h),border_radius=4)
            pygame.draw.rect(screen,col,(x,y,int(w*frac),h),border_radius=4)
        bar(16,16,300,14,(player.hp/MAX_HP) if player.alive else 0.0, BLUE if player.team=='ATT' else RED)
        draw_minimap(player)

        if player.lock_reason=='plant' and bomb.state=='idle':
            t=max(0,min(PLANT_HOLD_MS, now-player.lock_start))
            pygame.draw.rect(screen,(50,50,50),(20,VIEW_H-60,320,16),border_radius=4)
            pygame.draw.rect(screen,(0,180,255),(20,VIEW_H-60,int(320*t/PLANT_HOLD_MS),16),border_radius=4)
            screen.blit(font.render("PLANTING...",True,WHITE),(24,VIEW_H-80))
        if player.lock_reason=='defuse' and bomb.state=='planted':
            t=max(0,min(DEFUSE_HOLD_MS, now-player.lock_start))
            pygame.draw.rect(screen,(50,50,50),(20,VIEW_H-60,320,16),border_radius=4)
            pygame.draw.rect(screen,(0,255,120),(20,VIEW_H-60,int(320*t/DEFUSE_HOLD_MS),16),border_radius=4)
            screen.blit(font.render("DEFUSING...",True,WHITE),(24,VIEW_H-80))
        if player.lock_reason=='revive' and player.reviving_target is not None:
            t=max(0,min(REVIVE_MS, now-player.lock_start))
            pygame.draw.rect(screen,(50,50,50),(20,VIEW_H-88,320,16),border_radius=4)
            pygame.draw.rect(screen,(255,220,80),(20,VIEW_H-88,int(320*t/REVIVE_MS),16),border_radius=4)
            screen.blit(font.render("REVIVING...",True,WHITE),(24,VIEW_H-108))

        for side in (attackers, defenders):
            for ag in side:
                if ag.lock_reason=='revive' and ag.reviving_target is not None and not ag.is_player:
                    t=max(0,min(REVIVE_MS, now-ag.lock_start))
                    tgt=ag.reviving_target
                    pygame.draw.rect(screen,(40,40,40),(tgt.x-24-cam_x,tgt.y-40-cam_y,48,8))
                    pygame.draw.rect(screen,(255,220,80),(tgt.x-24-cam_x,tgt.y-40-cam_y,int(48*t/REVIVE_MS),8))

        if round_over:
            t = big_font.render(winner_text or "Round Over", True, YELLOW)
            screen.blit(t,(VIEW_W//2 - t.get_width()//2, VIEW_H//2 - t.get_height()//2))
            screen.blit(font.render("Press F5 to restart | ESC to quit", True, WHITE),(VIEW_W//2-160, VIEW_H//2+40))

        pygame.display.flip()
    pygame.quit(); sys.exit()

if __name__=='__main__':
    main()

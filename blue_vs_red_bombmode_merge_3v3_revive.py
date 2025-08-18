
import math, random, sys, heapq, pygame, time

# ==================== CONFIG ====================
WIDTH, HEIGHT = 1800, 1000   # larger map
GRID = 32
COLS, ROWS = WIDTH // GRID, HEIGHT // GRID
FPS = 60

RADIUS = 16
PLAYER_SPEED = 3.3
BOT_SPEED = 3.1
LOW_HP_SPEED = 1.6      # slowed when low HP

BULLET_SPEED = 7.5
BULLET_RADIUS = 5
BULLET_COOLDOWN = 220
BULLET_DAMAGE = 12

MAX_HP = 100
LOW_HP_THRESH = 28

# Perception
FOV_DEGREES = 100
FOV_RANGE = 560
HEARING_RADIUS = 420

# Bomb rules
BOMB_ZONE_RADIUS_CELLS = 5
PLANT_HOLD_MS = 5_000
DEFUSE_HOLD_MS = 10_000
BOMB_TIMER_MS  = 30_000

# Revive rules
REVIVE_MS = 10_000
REVIVE_RANGE = 70
DOWNED_TIMEOUT_MS = 5_000

# Colors
WHITE=(255,255,255); GRID_DARK=(30,30,32); GRID_LINE=(36,36,38)
WALL_DARK=(74,76,84); WALL_EDGE=(130,130,140)
BLUE=(40,150,255); RED=(235,60,60); GREEN=(70,200,100)
YELLOW=(250,210,70); CYAN=(60,220,220); ORANGE=(255,150,60)
GREY=(170,170,170); BLUE_BOT=(110,185,255); RED_BOT=(255,135,135)

pygame.init()
pygame.display.set_caption("Blue vs Red — 3v3 BombMode + Revive")
screen=pygame.display.set_mode((WIDTH,HEIGHT))
clock=pygame.time.Clock()
font=pygame.font.SysFont("consolas",18)
big_font=pygame.font.SysFont("consolas",40,bold=True)

# ==================== UTILS ====================
def clamp(v,a,b): return max(a,min(b,v))
def vec_len(v): return math.hypot(v[0],v[1])
def norm_vec(v):
    l=vec_len(v)
    return (0.0,0.0) if l==0 else (v[0]/l,v[1]/l)

def rect_edges(r):
    x,y,w,h=r
    return [((x,y),(x+w,y)),((x+w,y),(x+w,y+h)),((x+w,y+h),(x,y+h)),((x,y+h),(x,y))]

def seg_intersect(a1,a2,b1,b2):
    def cross(u,v): return u[0]*v[1]-u[1]*v[0]
    r=(a2[0]-a1[0],a2[1]-a1[1]); s=(b2[0]-b1[0],b2[1]-b1[1])
    denom=cross(r,s)
    if denom==0: return False
    t=cross((b1[0]-a1[0],b1[1]-a1[1]),s)/denom
    u=cross((b1[0]-a1[0],b1[1]-a1[1]),r)/denom
    return 0<t<1 and 0<u<1

def circle_rect_collision(cx,cy,r,rect):
    rx,ry,rw,rh=rect
    nx=clamp(cx,rx,rx+rw); ny=clamp(cy,ry,ry+rh)
    dx,dy=cx-nx,cy-ny
    return dx*dx+dy*dy<=r*r

def resolve_circle_rect_collision(pos,r,rect):
    cx,cy=pos; rx,ry,rw,rh=rect
    nx=clamp(cx,rx,rx+rw); ny=clamp(cy,ry,ry+rh)
    dx,dy=cx-nx,cy-ny; d2=dx*dx+dy*dy
    if d2>r*r or d2==0: return (cx,cy)
    d=math.sqrt(d2); over=r-d
    ux,uy=(dx/d,dy/d) if d!=0 else (1,0)
    return (cx+ux*over, cy+uy*over)

def has_line_of_sight(p1,p2,walls):
    for rect in walls:
        for e1,e2 in rect_edges(rect):
            if seg_intersect(p1,p2,e1,e2): return False
    return True

def angle_between(u,v):
    ul=vec_len(u); vl=vec_len(v)
    if ul==0 or vl==0: return 180.0
    dot=u[0]*v[0]+u[1]*v[1]
    c=clamp(dot/(ul*vl),-1.0,1.0)
    return math.degrees(math.acos(c))

def sees(A,B,walls):
    if not getattr(B, "alive", False): return False
    dx,dy=B.x-A.x,B.y-A.y
    if dx*dx+dy*dy>FOV_RANGE*FOV_RANGE: return False
    if angle_between(A.dir,(dx,dy))>FOV_DEGREES*0.5: return False
    if not has_line_of_sight((A.x,A.y),(B.x,B.y),walls): return False
    return True

# ==================== MAP ====================
def build_static_map():
    walls=[]; border=18
    walls += [pygame.Rect(0,0,WIDTH,border), pygame.Rect(0,HEIGHT-border,WIDTH,border),
              pygame.Rect(0,0,border,HEIGHT), pygame.Rect(WIDTH-border,0,border,HEIGHT)]
    walls += [
        pygame.Rect(320, 160, 360, 26),
        pygame.Rect(WIDTH-680, 160, 360, 26),
        pygame.Rect(460, HEIGHT//2-200, WIDTH-920, 24),
        pygame.Rect(460, HEIGHT//2+200, WIDTH-920, 24),
        pygame.Rect(WIDTH//2-12, 240, 24, 180),
        pygame.Rect(WIDTH//2-12, HEIGHT-520, 24, 220),
        pygame.Rect(580, HEIGHT-220, WIDTH-1160, 18),
        pygame.Rect(260, HEIGHT//2-40, 160, 18),
        pygame.Rect(WIDTH-420, HEIGHT//2-40, 160, 18),
        # extra pillars
        pygame.Rect(300, 350, 24, 160),
        pygame.Rect(WIDTH-324, 350, 24, 160),
    ]
    return walls

WALLS = build_static_map()

# ==================== GRID & PATHFIND ====================
def build_grid(walls):
    grid=[[True for _ in range(ROWS)] for _ in range(COLS)]
    for c in range(COLS):
        for r in range(ROWS):
            cell=pygame.Rect(c*GRID,r*GRID,GRID,GRID)
            for w in walls:
                if cell.colliderect(w.inflate(RADIUS*2,RADIUS*2)):
                    grid[c][r]=False; break
    return grid

def pos_to_cell(p):
    x,y=p; return (clamp(int(x//GRID),0,COLS-1), clamp(int(y//GRID),0,ROWS-1))

def cell_center(c,r): return (c*GRID+GRID//2, r*GRID+GRID//2)

def astar(grid,start,goal):
    if start==goal: return [start]
    if not grid[goal[0]][goal[1]]: return None
    dirs=[(1,0),(-1,0),(0,1),(0,-1)]
    openh=[(0,start)]; came={start:None}; g={start:0}
    def h(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
    while openh:
        _,cur=heapq.heappop(openh)
        if cur==goal:
            path=[]; 
            while cur: path.append(cur); cur=came[cur]
            return list(reversed(path))
        for d in dirs:
            nb=(cur[0]+d[0],cur[1]+d[1])
            if not (0<=nb[0]<COLS and 0<=nb[1]<ROWS): continue
            if not grid[nb[0]][nb[1]]: continue
            ng=g[cur]+1
            if nb not in g or ng<g[nb]:
                g[nb]=ng; came[nb]=cur
                heapq.heappush(openh,(ng+h(nb,goal),nb))
    return None

def nearest_passable_cell(grid, cell, max_ring=20):
    cx,cy=cell
    if grid[cx][cy]: return (cx,cy)
    for r in range(1,max_ring+1):
        for dx in range(-r,r+1):
            for dy in (-r,r):
                x=cx+dx; y=cy+dy
                if 0<=x<COLS and 0<=y<ROWS and grid[x][y]: return (x,y)
        for dy in range(-r+1,r):
            for dx in (-r,r):
                x=cx+dx; y=cy+dy
                if 0<=x<COLS and 0<=y<ROWS and grid[x][y]: return (x,y)
    return (cx,cy)

def collide_with_walls_circle(x,y,r,walls):
    nx,ny=x,y
    for rect in walls:
        if circle_rect_collision(nx,ny,r,rect):
            nx,ny=resolve_circle_rect_collision((nx,ny),r,rect)
    return nx,ny

# ==================== ENTITIES ====================
class Bullet:
    __slots__=("x","y","vx","vy","team","dead")
    def __init__(self,x,y,vx,vy,team):
        self.x,self.y=x,y; self.vx,self.vy=vx,vy
        self.team=team; self.dead=False
    def update(self,walls):
        self.x+=self.vx; self.y+=self.vy
        if not (0<=self.x<=WIDTH and 0<=self.y<=HEIGHT): self.dead=True; return
        for rect in walls:
            if circle_rect_collision(self.x,self.y,BULLET_RADIUS,rect): self.dead=True; return
    def draw(self,surf): pygame.draw.circle(surf, WHITE,(int(self.x),int(self.y)),BULLET_RADIUS)

class Agent:
    def __init__(self,x,y,color,team,is_player=False,name=""):
        self.x,self.y=x,y; self.color=color; self.r=RADIUS
        self.hp=MAX_HP; self.last_shot=0; self.dir=(1,0)
        self.alive=True; self.downed=False
        self.downed_at=0
        self.removed=False
        self.team=team; self.is_player=is_player; self.name=name
        self.lock_reason=None; self.lock_start=0
        self.reviving_target=None
        self.last_known_enemy=None
    @property
    def pos(self): return (self.x,self.y)
    def effective_speed(self, base):
        return LOW_HP_SPEED if self.hp<=LOW_HP_THRESH else base
    def take_damage(self,dmg):
        if not self.alive: return
        self.hp=max(0,self.hp-dmg)
        if self.lock_reason in ("plant","defuse","revive"):
            self.lock_reason=None
            self.reviving_target=None
        if self.hp<=0:
            self.downed=True; self.alive=False  # cannot act; can be revived
            self.downed_at=pygame.time.get_ticks()
            self.reviving_target=None
    def revive(self):
        self.hp=MAX_HP//2; self.alive=True; self.downed=False
        self.downed_at=0
        self.reviving_target=None
    def move(self, keys):
        if not self.alive or self.lock_reason is not None or self.downed: return
        if self.is_player:
            mvx=(keys[pygame.K_d]-keys[pygame.K_a])*self.effective_speed(PLAYER_SPEED)
            mvy=(keys[pygame.K_s]-keys[pygame.K_w])*self.effective_speed(PLAYER_SPEED)
        else:
            mvx=mvy=0
        nx,ny=self.x+mvx, self.y+mvy
        self.x,self.y=collide_with_walls_circle(nx,ny,RADIUS,WALLS)
        if mvx!=0 or mvy!=0:
            l=math.hypot(mvx,mvy); self.dir=(mvx/l,mvy/l) if l else self.dir
    def shoot(self,target_pos,now,bullets):
        if now - self.last_shot < BULLET_COOLDOWN or not self.alive or self.downed: return
        if self.lock_reason is not None: return
        v=norm_vec((target_pos[0]-self.x,target_pos[1]-self.y))
        if v==(0,0): return
        self.last_shot=now
        bullets.append(Bullet(self.x+v[0]*(self.r+6), self.y+v[1]*(self.r+6),
                              v[0]*BULLET_SPEED, v[1]*BULLET_SPEED, self.team))
    def draw(self,surf):
        col = self.color
        if self.downed:
            col=(120,120,120)
        elif not self.alive:
            col=(60,60,60)
        pygame.draw.circle(surf,col,(int(self.x),int(self.y)),self.r)
        fx=self.x+self.dir[0]*self.r*1.4; fy=self.y+self.dir[1]*self.r*1.4
        pygame.draw.line(surf,WHITE,(self.x,self.y),(fx,fy),2 if self.alive and not self.downed else 1)
        # HP bar & name
        if self.alive:
            pygame.draw.rect(surf,(40,40,40),(self.x-20,self.y-28,40,6))
            pygame.draw.rect(surf,GREEN,(self.x-20,self.y-28,40*self.hp/MAX_HP,6))
        status = " (DOWN)" if self.downed else (" (DEAD)" if not self.alive else "")
        label=font.render(self.name + status,True,GREY)
        surf.blit(label,(self.x-label.get_width()/2,self.y+self.r+3))

# ==================== BOMB STATE ====================
class BombState:
    def __init__(self, zone_center):
        self.zone_center = zone_center
        self.state="idle"    # idle, planted, defused, exploded
        self.planted_time=0
        self.planter_team=None
    def in_zone(self, p):
        return pygame.Vector2(p[0],p[1]).distance_to(self.zone_center) <= BOMB_ZONE_RADIUS_CELLS*GRID - 6
    def commit_plant(self, team):
        self.state="planted"; self.planter_team=team; self.planted_time=pygame.time.get_ticks()
    def commit_defuse(self): self.state="defused"

# ==================== BOT AI ====================
def choose_patrol_goal(grid):
    for _ in range(200):
        c=random.randrange(COLS); r=random.randrange(ROWS)
        if grid[c][r]: return (c,r)
    return (COLS//2, ROWS//2)

def separation_force(agent, friends, radius=60, strength=0.8):
    fx=fy=0.0
    for f in friends:
        if f is agent or not (f.alive or f.downed): continue
        dx=agent.x-f.x; dy=agent.y-f.y; d2=dx*dx+dy*dy
        if d2>1 and d2<radius*radius:
            inv=1.0/max(1.0, math.sqrt(d2))
            fx += dx*inv*strength
            fy += dy*inv*strength
    return (fx,fy)

def bot_ai(agent, enemies, friends, walls, bullets, grid, nav, bomb:BombState):
    # skip downed/dead
    if agent.downed or not (agent.alive or agent.downed): return
    now=pygame.time.get_ticks()

    # revive nearby friend if any downed
    nearest_downed=None; best=1e9
    for fr in friends:
        if fr.downed:
            d = (agent.x-fr.x)**2 + (agent.y-fr.y)**2
            if d<best: best=d; nearest_downed=fr
    if nearest_downed is not None and best <= (REVIVE_RANGE*REVIVE_RANGE*4):
        # move to revive
        target_cell = pos_to_cell(nearest_downed.pos)
        do_revive=True
    else:
        do_revive=False
        # Perception
        for e in enemies:
            if e.alive and sees(agent, e, walls):
                agent.last_known_enemy=e.pos; break

        # Intent
        target_cell=None; do_plant=False; do_defuse=False
        if bomb.state=="idle":
            if agent.team=="ATT":
                if bomb.in_zone(agent.pos): do_plant=True
                else: target_cell = pos_to_cell(bomb.zone_center)
            else:
                target_cell = pos_to_cell(agent.last_known_enemy or bomb.zone_center)
        elif bomb.state=="planted":
            if agent.team=="DEF":
                if bomb.in_zone(agent.pos): do_defuse=True
                else: target_cell = pos_to_cell(bomb.zone_center)
            else:
                target_cell = pos_to_cell(agent.last_known_enemy or (bomb.zone_center[0]+random.randint(-200,200),
                                                                     bomb.zone_center[1]+random.randint(-200,200)))
        else:
            target_cell = pos_to_cell(agent.last_known_enemy or cell_center(*choose_patrol_goal(grid)))

    # Movement (A* + separation; skip if locked)
    if agent.lock_reason is None and agent.alive and not agent.downed:
        if do_revive:
            goal = nearest_passable_cell(grid, target_cell)
        else:
            goal = nearest_passable_cell(grid, target_cell) if 'target_cell' in locals() and target_cell is not None else None
        start = pos_to_cell(agent.pos)
        if goal is not None:
            recalc = (nav["goal"]!=goal or nav["path"] is None or now - nav["last_compute"] > 300)
            if recalc:
                nav["path"]=astar(grid,start,goal)
                nav["goal"]=goal; nav["idx"]=0; nav["last_compute"]=now
            path=nav["path"]
            if path:
                idx=nav["idx"]
                if idx>=len(path): idx=len(path)-1
                wp=cell_center(*path[idx])
                to_wp=(wp[0]-agent.x, wp[1]-agent.y)
                if vec_len(to_wp)<6 and idx<len(path)-1:
                    idx+=1; nav["idx"]=idx; wp=cell_center(*path[idx]); to_wp=(wp[0]-agent.x, wp[1]-agent.y)
                steer=norm_vec(to_wp)
            else:
                steer=(0.0,0.0)
        else:
            steer=(0.0,0.0)

        # separation to avoid stacking
        sep = separation_force(agent, friends)
        steer = (steer[0]+sep[0], steer[1]+sep[1])
        l=vec_len(steer)
        if l>0: steer=(steer[0]/l, steer[1]/l)

        speed = agent.effective_speed(BOT_SPEED)
        vx,vy=steer[0]*speed, steer[1]*speed
        nx,ny=agent.x+vx, agent.y+vy
        agent.x,agent.y=collide_with_walls_circle(nx,ny,RADIUS,walls)
        if vec_len((vx,vy))>0: agent.dir=norm_vec((vx,vy))

    # Combat (if see enemy and not reviving)
    if not do_revive and agent.lock_reason is None and agent.alive:
        target=None
        for e in enemies:
            if e.alive and sees(agent, e, walls) and has_line_of_sight(agent.pos, e.pos, walls):
                target=e; break
        if target:
            agent.shoot(target.pos, now, bullets)

    # Revive lock
    if do_revive:
        if math.hypot(agent.x-nearest_downed.x, agent.y-nearest_downed.y) <= REVIVE_RANGE:
            if agent.lock_reason is None:
                agent.lock_reason="revive"; agent.lock_start=now; agent.reviving_target=nearest_downed
            elif agent.lock_reason=="revive" and agent.reviving_target is nearest_downed:
                if now - agent.lock_start >= REVIVE_MS:
                    nearest_downed.revive(); agent.lock_reason=None; agent.reviving_target=None
        else:
            if agent.lock_reason=="revive": agent.lock_reason=None; agent.reviving_target=None

    # Bomb plant/defuse (cancel on damage handled in take_damage)
    if not do_revive:
        if bomb.state=="idle" and agent.team=="ATT" and bomb.in_zone(agent.pos):
            if agent.lock_reason is None: agent.lock_reason="plant"; agent.lock_start=now
            if now - agent.lock_start >= PLANT_HOLD_MS:
                bomb.commit_plant(agent.team); agent.lock_reason=None
        elif bomb.state=="planted" and agent.team=="DEF" and bomb.in_zone(agent.pos):
            if agent.lock_reason is None: agent.lock_reason="defuse"; agent.lock_start=now
            if now - agent.lock_start >= DEFUSE_HOLD_MS:
                bomb.commit_defuse(); agent.lock_reason=None
        else:
            if agent.lock_reason in ("plant","defuse"): agent.lock_reason=None

# ==================== SETUP ====================
def reset_round():
    walls = build_static_map()
    grid  = build_grid(walls)
    zone_cell = nearest_passable_cell(grid, pos_to_cell((WIDTH//2, HEIGHT//2)))
    zone_center = cell_center(*zone_cell)
    A = [
        Agent(220, HEIGHT-180, BLUE, "ATT", is_player=True, name="YOU"),
        Agent(280, HEIGHT-240, BLUE_BOT, "ATT", name="ALLY-1"),
        Agent(340, HEIGHT-180, BLUE_BOT, "ATT", name="ALLY-2"),
    ]
    D = [
        Agent(WIDTH-240, 180, RED, "DEF", name="ENEMY-1"),
        Agent(WIDTH-300, 260, RED_BOT, "DEF", name="ENEMY-2"),
        Agent(WIDTH-340, 180, RED_BOT, "DEF", name="ENEMY-3"),
    ]
    bomb = BombState(zone_center)
    navs = {id(a):{"path":None,"goal":None,"idx":0,"last_compute":0} for a in A[1:]+D}
    return walls, grid, zone_center, A, D, bomb, navs

# ==================== MAIN ====================
def alive(lst): return [a for a in lst if a.alive]
def active_or_downed(lst): return [a for a in lst if (a.alive or a.downed)]

def main():
    walls, grid, zone_center, attackers, defenders, bomb, navs = reset_round()
    bullets=[]
    round_over=False; winner_text=""
    running=True
    while running:
        dt=clock.tick(FPS)
        for event in pygame.event.get():
            if event.type==pygame.QUIT: running=False
            elif event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE: running=False
                if event.key==pygame.K_r:
                    # player revive action when near downed ally
                    pass  # handled continuously below for hold-to-revive
                if event.key==pygame.K_F5:
                    walls, grid, zone_center, attackers, defenders, bomb, navs = reset_round()
                    bullets=[]; round_over=False; winner_text=""

        keys=pygame.key.get_pressed()

        if not round_over:
            # Player control
            player = attackers[0]
            player.move(keys)

            # Aim & shoot
            mx,my=pygame.mouse.get_pos()
            aim=norm_vec((mx-player.x, my-player.y))
            if aim!=(0,0): player.dir=aim
            if pygame.mouse.get_pressed(num_buttons=3)[0] and player.alive and player.lock_reason is None:
                now=pygame.time.get_ticks()
                player.shoot((mx,my), now, bullets)

            # Player plant/defuse/revive (hold keys)
            now=pygame.time.get_ticks()
            hold4 = keys[pygame.K_4] or keys[pygame.K_KP4]
            holdR = keys[pygame.K_r]
            # revive nearest downed ally
            nearest=None; best=1e9
            for ally in attackers:
                if ally.downed:
                    d=(ally.x-player.x)**2+(ally.y-player.y)**2
                    if d<best: best=d; nearest=ally
            if holdR and nearest and best<=REVIVE_RANGE*REVIVE_RANGE and player.alive and player.lock_reason in (None,"revive"):
                if player.lock_reason is None: player.lock_reason="revive"; player.lock_start=now; player.reviving_target=nearest
                elif now - player.lock_start >= REVIVE_MS and player.reviving_target is nearest:
                    nearest.revive(); player.lock_reason=None; player.reviving_target=None
            else:
                if player.lock_reason=="revive" and not holdR: player.lock_reason=None; player.reviving_target=None

            if player.alive and hold4 and bomb.in_zone(player.pos) and player.lock_reason in (None,"plant","defuse"):
                if bomb.state=="idle" and player.team=="ATT":
                    if player.lock_reason is None: player.lock_reason="plant"; player.lock_start=now
                    elif now - player.lock_start >= PLANT_HOLD_MS:
                        bomb.commit_plant(player.team); player.lock_reason=None
                elif bomb.state=="planted" and player.team=="DEF":
                    if player.lock_reason is None: player.lock_reason="defuse"; player.lock_start=now
                    elif now - player.lock_start >= DEFUSE_HOLD_MS:
                        bomb.commit_defuse(); player.lock_reason=None
            else:
                if player.lock_reason in ("plant","defuse") and not hold4:
                    player.lock_reason=None

            # Bots
            for a in attackers[1:]:
                bot_ai(a, defenders, attackers, walls, bullets, grid, navs[id(a)], bomb)
            for d in defenders:
                bot_ai(d, attackers, defenders, walls, bullets, grid, navs[id(d)], bomb)

            # Bullets & damage
            for b in bullets:
                b.update(walls)
                if b.dead: continue
                targets = defenders if b.team=="ATT" else attackers
                for t in targets:
                    if (t.alive or t.downed) and pygame.Vector2(b.x,b.y).distance_to(t.pos) <= RADIUS+BULLET_RADIUS:
                        if t.alive: t.take_damage(BULLET_DAMAGE)
                        b.dead=True; break
            bullets=[b for b in bullets if not b.dead]

            # Downed timeout -> death
            tick = pygame.time.get_ticks()
            for ag in attackers + defenders:
                if ag.downed and tick - ag.downed_at >= DOWNED_TIMEOUT_MS:
                    ag.downed=False
                    ag.alive=False
                    ag.hp=0
                    ag.reviving_target=None

            # Bomb timer
            if bomb.state=="planted" and pygame.time.get_ticks() - bomb.planted_time >= BOMB_TIMER_MS:
                bomb.state="exploded"

            # Win logic
            A_active = len(active_or_downed(attackers))
            D_active = len(active_or_downed(defenders))
            A_alive = len(alive(attackers))
            D_alive = len(alive(defenders))

            if bomb.state=="idle":
                if A_alive==0 and D_alive>0 and all(not a.downed for a in attackers):
                    winner_text="DEFENDERS WIN — Attackers eliminated"; round_over=True
                elif D_alive==0 and A_alive>0 and all(not d.downed for d in defenders):
                    winner_text="ATTACKERS WIN — Defenders eliminated"; round_over=True
            elif bomb.state=="planted":
                if D_alive==0 and all(not d.downed for d in defenders):
                    winner_text="ATTACKERS WIN — All defenders down"; round_over=True
                elif bomb.state=="exploded":
                    winner_text="ATTACKERS WIN — Bomb exploded"; round_over=True
                elif bomb.state=="defused":
                    winner_text="DEFENDERS WIN — Bomb defused"; round_over=True

        # ===== DRAW =====
        screen.fill(GRID_DARK)
        for x in range(0, WIDTH, 48): pygame.draw.line(screen, GRID_LINE, (x,0), (x,HEIGHT))
        for y in range(0, HEIGHT, 48): pygame.draw.line(screen, GRID_LINE, (0,y), (WIDTH,y))
        for rect in walls:
            pygame.draw.rect(screen, WALL_DARK, rect); pygame.draw.rect(screen, WALL_EDGE, rect, 2)

        # Zone
        pygame.draw.circle(screen, (60,60,60), zone_center, BOMB_ZONE_RADIUS_CELLS*GRID, 2)
        pygame.draw.circle(screen, (120,120,160), zone_center, 8)

        # Entities
        for a in attackers: a.draw(screen)
        for d in defenders: d.draw(screen)
        for b in bullets: b.draw(screen)

        # HUD & progress
        def bar(x,y,w,h,frac,col):
            pygame.draw.rect(screen,(40,40,40),(x,y,w,h),border_radius=4)
            pygame.draw.rect(screen,col,(x,y,int(w*frac),h),border_radius=4)

        player = attackers[0]
        bar(16,16,300,14,(player.hp/MAX_HP) if player.alive else 0.0, BLUE)
        screen.blit(font.render(f"YOU {player.hp if player.alive else 0}/{MAX_HP} | Hold '4' to PLANT/DEFUSE | Hold 'R' near ally to REVIVE (10s)", True, WHITE), (18,34))

        # Bottom status
        status=""
        if bomb.state=="idle":
            status="Bomb idle — Attackers plant at site."
        elif bomb.state=="planted":
            remain = max(0, (BOMB_TIMER_MS - (pygame.time.get_ticks() - bomb.planted_time))//1000)
            status=f"Bomb planted — Explodes in {remain}s. Defenders hold '4' to defuse (10s)."
        elif bomb.state=="defused": status="Bomb defused."
        elif bomb.state=="exploded": status="Bomb exploded."
        screen.blit(font.render(status, True, GREY), (20, HEIGHT-28))

        # Progress bars on actions
        now=pygame.time.get_ticks()
        # player bars
        if player.lock_reason=="plant" and bomb.state=="idle":
            t=max(0, min(PLANT_HOLD_MS, now - player.lock_start))
            pygame.draw.rect(screen,(50,50,50),(20,HEIGHT-60,320,16),border_radius=4)
            pygame.draw.rect(screen,(0,180,255),(20,HEIGHT-60,int(320*t/PLANT_HOLD_MS),16),border_radius=4)
            screen.blit(font.render("PLANTING...", True, WHITE),(24,HEIGHT-80))
        if player.lock_reason=="defuse" and bomb.state=="planted":
            t=max(0, min(DEFUSE_HOLD_MS, now - player.lock_start))
            pygame.draw.rect(screen,(50,50,50),(20,HEIGHT-60,320,16),border_radius=4)
            pygame.draw.rect(screen,(0,255,120),(20,HEIGHT-60,int(320*t/DEFUSE_HOLD_MS),16),border_radius=4)
            screen.blit(font.render("DEFUSING...", True, WHITE),(24,HEIGHT-80))
        if player.lock_reason=="revive" and player.reviving_target is not None:
            t=max(0, min(REVIVE_MS, now - player.lock_start))
            pygame.draw.rect(screen,(50,50,50),(20,HEIGHT-88,320,16),border_radius=4)
            pygame.draw.rect(screen,(255,220,80),(20,HEIGHT-88,int(320*t/REVIVE_MS),16),border_radius=4)
            screen.blit(font.render("REVIVING...", True, WHITE),(24,HEIGHT-108))

        # draw progress over downed targets being revived by bots
        for side in (attackers, defenders):
            for ag in side:
                if ag.lock_reason=="revive" and ag.reviving_target is not None:
                    t=max(0,min(REVIVE_MS, now - ag.lock_start))
                    tgt=ag.reviving_target
                    pygame.draw.rect(screen,(40,40,40),(tgt.x-24,tgt.y-40,48,8))
                    pygame.draw.rect(screen,(255,220,80),(tgt.x-24,tgt.y-40,int(48*t/REVIVE_MS),8))

        if round_over:
            t = big_font.render(winner_text or "Round Over", True, YELLOW)
            screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - t.get_height()//2))
            screen.blit(font.render("Press F5 to restart | ESC to quit", True, WHITE), (WIDTH//2-160, HEIGHT//2+40))

        pygame.display.flip()

    pygame.quit(); sys.exit()

if __name__ == "__main__":
    main()

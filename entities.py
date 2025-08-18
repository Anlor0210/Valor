import pygame, math
from config import (RADIUS, BULLET_SPEED, BULLET_RADIUS, BULLET_COOLDOWN,
                    MAX_HP, LOW_HP_THRESH, PLAYER_SPEED, REVIVE_MS, REVIVE_RANGE,
                    WIDTH, HEIGHT, GRID)
from map import move_with_collision

WHITE=(255,255,255)
GREEN=(70,200,100)
GREY=(170,170,170)

class Bullet:
    __slots__=("x","y","vx","vy","team","dead")
    def __init__(self,x,y,vx,vy,team):
        self.x,self.y=x,y; self.vx,self.vy=vx,vy
        self.team=team; self.dead=False
    def update(self,walls):
        self.x+=self.vx; self.y+=self.vy
        if not (0<=self.x<=WIDTH and 0<=self.y<=HEIGHT):
            self.dead=True; return
        for rect in walls:
            if rect.collidepoint(self.x,self.y):
                self.dead=True; return
    def draw(self,surf,cam):
        pygame.draw.circle(surf,WHITE,(int(self.x-cam[0]),int(self.y-cam[1])),BULLET_RADIUS)

class Agent:
    def __init__(self,x,y,color,team,is_player=False,name=""):
        self.x,self.y=x,y; self.color=color; self.r=RADIUS
        self.hp=MAX_HP; self.last_shot=0; self.dir=(1,0)
        self.alive=True; self.downed=False
        self.downed_at=0
        self.bleed_paused=0
        self.bleed_paused_start=None
        self.removed=False
        self.team=team; self.is_player=is_player; self.name=name
        self.lock_reason=None; self.lock_start=0
        self.reviving_target=None
        self.last_known_enemy=None
    @property
    def pos(self): return (self.x,self.y)
    def distance_to(self, other):
        return math.hypot(self.x-other.x, self.y-other.y)
    def effective_speed(self, base):
        return 1.6 if self.hp<=LOW_HP_THRESH else base
    def pause_bleedout(self):
        if self.bleed_paused_start is None:
            self.bleed_paused_start=pygame.time.get_ticks()
    def resume_bleedout(self):
        if self.bleed_paused_start is not None:
            self.bleed_paused += pygame.time.get_ticks()-self.bleed_paused_start
            self.bleed_paused_start=None
    def take_damage(self,dmg):
        if not self.alive:
            return
        self.hp=max(0,self.hp-dmg)
        if self.lock_reason in ("plant","defuse","revive"):
            if self.reviving_target:
                self.reviving_target.resume_bleedout()
            self.lock_reason=None; self.reviving_target=None
        if self.hp<=0:
            self.downed=True; self.alive=False
            self.downed_at=pygame.time.get_ticks()
            self.bleed_paused=0; self.bleed_paused_start=None
            self.reviving_target=None
    def revive(self):
        self.hp=MAX_HP//2; self.alive=True; self.downed=False
        self.downed_at=0; self.bleed_paused=0; self.bleed_paused_start=None
        self.reviving_target=None
    def move_player(self, keys, walls):
        if not self.alive or self.lock_reason is not None or self.downed:
            return
        mvx=(keys[pygame.K_d]-keys[pygame.K_a])*self.effective_speed(PLAYER_SPEED)
        mvy=(keys[pygame.K_s]-keys[pygame.K_w])*self.effective_speed(PLAYER_SPEED)
        self.x,self.y=move_with_collision(self.x,self.y,mvx,mvy,self.r,walls)
        if mvx!=0 or mvy!=0:
            l=math.hypot(mvx,mvy); self.dir=(mvx/l,mvy/l) if l else self.dir
    def shoot(self,target_pos,now,bullets):
        if now-self.last_shot<BULLET_COOLDOWN or not self.alive or self.downed:
            return
        if self.lock_reason is not None:
            return
        dx,dy=target_pos[0]-self.x, target_pos[1]-self.y
        l=math.hypot(dx,dy)
        if l==0:
            return
        vx,vy=dx/l, dy/l
        self.last_shot=now
        bullets.append(Bullet(self.x+vx*(self.r+6), self.y+vy*(self.r+6), vx*BULLET_SPEED, vy*BULLET_SPEED, self.team))
    def draw(self,surf,cam,font):
        col=self.color
        if self.downed: col=(120,120,120)
        elif not self.alive: col=(60,60,60)
        pygame.draw.circle(surf,col,(int(self.x-cam[0]),int(self.y-cam[1])),self.r)
        fx=self.x+self.dir[0]*self.r*1.4; fy=self.y+self.dir[1]*self.r*1.4
        pygame.draw.line(surf,WHITE,(self.x-cam[0],self.y-cam[1]),(fx-cam[0],fy-cam[1]),2 if self.alive and not self.downed else 1)
        if self.alive:
            pygame.draw.rect(surf,(40,40,40),(self.x-20-cam[0],self.y-28-cam[1],40,6))
            pygame.draw.rect(surf,GREEN,(self.x-20-cam[0],self.y-28-cam[1],40*self.hp/MAX_HP,6))
        status=" (DOWN)" if self.downed else (" (DEAD)" if not self.alive else "")
        label=font.render(self.name+status,True,GREY)
        surf.blit(label,(self.x-label.get_width()/2-cam[0], self.y+self.r+3-cam[1]))

class BombState:
    def __init__(self, zone_center, radius):
        self.zone_center=zone_center
        self.radius=radius
        self.state='idle'
        self.planted_time=0
        self.planter_team=None
    def in_zone(self,p):
        return pygame.Vector2(p[0],p[1]).distance_to(self.zone_center) <= self.radius*GRID - 6
    def commit_plant(self, team):
        self.state='planted'; self.planter_team=team; self.planted_time=pygame.time.get_ticks()
    def commit_defuse(self):
        self.state='defused'

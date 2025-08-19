import math, random, heapq, pygame
from config import (
    GRID,
    FOV_DEGREES,
    FOV_RANGE,
    BOT_SPEED,
    REVIVE_MS,
    REVIVE_RANGE,
    PLANT_MS,
    DEFUSE_MS,
    SEP_RADIUS,
    SEP_STRENGTH,
)
from map import (pos_to_cell, cell_center, nearest_passable_cell,
                 move_with_collision, has_line_of_sight)
from entities import Bullet

# vector helpers

def vec_len(v):
    return math.hypot(v[0], v[1])

def norm_vec(v):
    l=vec_len(v)
    return (0.0,0.0) if l==0 else (v[0]/l, v[1]/l)

def angle_between(u,v):
    ul=vec_len(u); vl=vec_len(v)
    if ul==0 or vl==0: return 180.0
    dot=u[0]*v[0]+u[1]*v[1]
    c=max(-1.0,min(1.0,dot/(ul*vl)))
    return math.degrees(math.acos(c))

def sees(A,B,walls):
    if not getattr(B, 'alive', False):
        return False
    dx,dy=B.x-A.x, B.y-A.y
    if dx*dx+dy*dy > FOV_RANGE*FOV_RANGE:
        return False
    if angle_between(A.dir,(dx,dy))>FOV_DEGREES*0.5:
        return False
    if not has_line_of_sight((A.x,A.y),(B.x,B.y),walls):
        return False
    return True

# A*

def astar(grid,start,goal):
    if start==goal:
        return [start]
    if not grid[goal[0]][goal[1]]:
        return None
    dirs=[(1,0),(-1,0),(0,1),(0,-1)]
    openh=[(0,start)]; came={start:None}; g={start:0}
    def h(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
    while openh:
        _,cur=heapq.heappop(openh)
        if cur==goal:
            path=[]
            while cur: path.append(cur); cur=came[cur]
            return list(reversed(path))
        for d in dirs:
            nb=(cur[0]+d[0],cur[1]+d[1])
            if not (0<=nb[0]<len(grid) and 0<=nb[1]<len(grid[0])):
                continue
            if not grid[nb[0]][nb[1]]:
                continue
            ng=g[cur]+1
            if nb not in g or ng<g[nb]:
                g[nb]=ng; came[nb]=cur
                heapq.heappush(openh,(ng+h(nb,goal),nb))
    return None

# avoidance

def separation_force(agent, friends, radius=SEP_RADIUS, strength=SEP_STRENGTH):
    fx=fy=0.0
    for f in friends:
        if f is agent or not (f.alive or f.downed):
            continue
        dx=agent.x-f.x; dy=agent.y-f.y; d2=dx*dx+dy*dy
        if 1<d2<radius*radius:
            inv=1.0/max(1.0, math.sqrt(d2))
            fx += dx*inv*strength
            fy += dy*inv*strength
    return (fx,fy)

# main AI

def bot_ai(agent, enemies, friends, walls, bullets, grid, nav, bomb):
    if agent.downed or not (agent.alive or agent.downed):
        return
    now=pygame.time.get_ticks()

    # check for downed ally
    nearest_downed=None; best=1e9
    for fr in friends:
        if fr.downed:
            d=(agent.x-fr.x)**2+(agent.y-fr.y)**2
            if d<best:
                best=d; nearest_downed=fr
    do_revive=False
    if nearest_downed is not None and best <= (REVIVE_RANGE*REVIVE_RANGE*4):
        target_cell=pos_to_cell(nearest_downed.pos)
        do_revive=True
    else:
        # perceive enemy
        for e in enemies:
            if e.alive and sees(agent,e,walls):
                agent.last_known_enemy=e.pos; break
        target_cell=None
        if bomb.state=='idle':
            if agent.team=='ATT':
                if bomb.in_zone(agent.pos):
                    do_plant=True
                else:
                    target_cell=pos_to_cell(bomb.zone_center)
            else:
                target_cell=pos_to_cell(agent.last_known_enemy or bomb.zone_center)
        elif bomb.state=='planted':
            if agent.team=='DEF':
                if bomb.in_zone(agent.pos):
                    do_defuse=True
                else:
                    target_cell=pos_to_cell(bomb.zone_center)
            else:
                target_cell=pos_to_cell(agent.last_known_enemy or bomb.zone_center)
        else:
            target_cell=pos_to_cell(agent.last_known_enemy or bomb.zone_center)
        do_plant=False; do_defuse=False

    # movement
    if agent.lock_reason is None and agent.alive and not agent.downed:
        goal = nearest_passable_cell(grid, target_cell) if target_cell else None
        start = pos_to_cell(agent.pos)
        if goal is not None:
            recalc = (nav['goal']!=goal or nav['path'] is None or now-nav['last_compute']>300)
            if recalc:
                nav['path']=astar(grid,start,goal)
                nav['goal']=goal; nav['idx']=0; nav['last_compute']=now
            path=nav['path']
            if path:
                idx=nav['idx']
                if idx>=len(path): idx=len(path)-1
                wp=cell_center(*path[idx])
                to_wp=(wp[0]-agent.x, wp[1]-agent.y)
                if vec_len(to_wp)<6 and idx<len(path)-1:
                    idx+=1; nav['idx']=idx; wp=cell_center(*path[idx]); to_wp=(wp[0]-agent.x, wp[1]-agent.y)
                steer=norm_vec(to_wp)
            else:
                steer=(0.0,0.0)
        else:
            steer=(0.0,0.0)
        sep=separation_force(agent,friends)
        steer=(steer[0]+sep[0], steer[1]+sep[1])
        l=vec_len(steer)
        if l>0:
            steer=(steer[0]/l, steer[1]/l)
        speed=agent.effective_speed(BOT_SPEED)
        vx,vy=steer[0]*speed, steer[1]*speed
        agent.x,agent.y=move_with_collision(agent.x,agent.y,vx,vy,agent.r,walls)
        if vec_len((vx,vy))>0:
            agent.dir=norm_vec((vx,vy))

    # combat
    if not do_revive and agent.lock_reason is None and agent.alive:
        target=None
        for e in enemies:
            if e.alive and sees(agent,e,walls) and has_line_of_sight(agent.pos,e.pos,walls):
                target=e; break
        if target:
            agent.shoot(target.pos, now, bullets)

    # revive lock
    if do_revive:
        if agent.distance_to(nearest_downed) <= REVIVE_RANGE:
            if agent.lock_reason is None:
                agent.lock_reason='revive'; agent.lock_start=now; agent.reviving_target=nearest_downed
                nearest_downed.pause_bleedout()
            elif agent.lock_reason=='revive' and agent.reviving_target is nearest_downed:
                if now-agent.lock_start>=REVIVE_MS:
                    nearest_downed.revive(); agent.lock_reason=None; agent.reviving_target=None
                    nearest_downed.resume_bleedout()
        else:
            if agent.lock_reason=='revive':
                agent.lock_reason=None; nearest_downed.resume_bleedout(); agent.reviving_target=None
    else:
        if agent.lock_reason=='revive' and agent.reviving_target is not None:
            agent.reviving_target.resume_bleedout()
            agent.lock_reason=None; agent.reviving_target=None

    # plant/defuse
    if not do_revive:
        if bomb.state=='idle' and agent.team=='ATT' and bomb.in_zone(agent.pos):
            if agent.lock_reason is None:
                agent.lock_reason='plant'; agent.lock_start=now
            if now-agent.lock_start>=PLANT_MS:
                bomb.commit_plant(agent.team); agent.lock_reason=None
        elif bomb.state=='planted' and agent.team=='DEF' and bomb.in_zone(agent.pos):
            if agent.lock_reason is None:
                agent.lock_reason='defuse'; agent.lock_start=now
            if now-agent.lock_start>=DEFUSE_MS:
                bomb.commit_defuse(); agent.lock_reason=None
        else:
            if agent.lock_reason in ('plant','defuse'):
                agent.lock_reason=None

import math, pygame, random
from config import WIDTH, HEIGHT, GRID, COLS, ROWS, RADIUS

# basic helpers

def clamp(v,a,b):
    return max(a, min(b, v))

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
    dx,dy=cx-nx, cy-ny
    return dx*dx+dy*dy <= r*r

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
            if seg_intersect(p1,p2,e1,e2):
                return False
    return True

# map building

def build_static_map():
    walls=[]; border=18
    walls += [pygame.Rect(0,0,WIDTH,border), pygame.Rect(0,HEIGHT-border,WIDTH,border),
              pygame.Rect(0,0,border,HEIGHT), pygame.Rect(WIDTH-border,0,border,HEIGHT)]
    # simple central rooms / corridors for placeholder
    walls += [
        pygame.Rect(800, 800, 1400, 40),
        pygame.Rect(800, HEIGHT-840, 1400, 40),
        pygame.Rect(800, 840, 40, HEIGHT-1680),
        pygame.Rect(WIDTH-840, 840, 40, HEIGHT-1680),
    ]
    return walls


def build_procedural_world(seed=None):
    """Very small placeholder procedural generator.

    The real project would create several themed areas and cover nodes.  For the
    unit tests we simply call :func:`build_static_map` and return the grid along
    with empty placeholders for the additional data.
    """

    if seed is not None:
        random.seed(seed)
    walls = build_static_map()
    grid = build_grid(walls)
    cover_nodes = []
    sites = {"A": None, "B": None}
    return walls, grid, cover_nodes, sites

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
    x,y=p
    return (clamp(int(x//GRID),0,COLS-1), clamp(int(y//GRID),0,ROWS-1))

def cell_center(c,r):
    return (c*GRID+GRID//2, r*GRID+GRID//2)

def nearest_passable_cell(grid, cell, max_ring=20):
    cx,cy=cell
    if grid[cx][cy]:
        return (cx,cy)
    for r in range(1,max_ring+1):
        for dx in range(-r,r+1):
            for dy in (-r,r):
                x=cx+dx; y=cy+dy
                if 0<=x<COLS and 0<=y<ROWS and grid[x][y]:
                    return (x,y)
        for dy in range(-r+1,r):
            for dx in (-r,r):
                x=cx+dx; y=cy+dy
                if 0<=x<COLS and 0<=y<ROWS and grid[x][y]:
                    return (x,y)
    return (cx,cy)

# movement with wall sliding

def move_with_collision(x,y,vx,vy,r,walls):
    nx=x+vx
    for rect in walls:
        if circle_rect_collision(nx,y,r,rect):
            nx, _ = resolve_circle_rect_collision((nx,y),r,rect)
    ny=y+vy
    for rect in walls:
        if circle_rect_collision(nx,ny,r,rect):
            _, ny = resolve_circle_rect_collision((nx,ny),r,rect)
    return nx, ny

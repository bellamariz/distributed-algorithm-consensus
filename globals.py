MAX_NODES = 10
SIMULATION_DURATION = 30
SIMULATION_RANGE_X = (-500, 500)
SIMULATION_RANGE_Y = (-500, 500)
SIMULATION_RANGE_Z = (0, 150)
COMMUNICATION_MEDIUM_RANGE = 30
GROUND_BASE_CORD = (0,0,0)
SENSORS_COORD_LIST = [
    (-150,  200,  0), # sensor 1
    (-250,   50,  0), # sensor 2
    (-250,  -50,  0), # sensor 3
    (-150, -200,  0), # sensor 4
    ( 150, -200,  0), # sensor 5
    ( 250,  -50,  0), # sensor 6
    ( 250,   50,  0), # sensor 7
    ( 150,  200,  0), # sensor 8
]
BASE_WAYPOINTS_COORD_LIST = [
    (-150,  200,  20), 
    (-250,   50,  20), 
    (-250,  -50,  20),
    (-150, -200,  20), 
    ( 150, -200,  20),
    ( 250,  -50,  20),
    ( 250,   50,  20),
    ( 150,  200,  20),
    (   0,    0,  20),
]

# BASE WAYPOINTS COORD LIST OPT 1, BUT +/- 30 ON X AND Y
BASE_WAYPOINTS_COORD_LIST_OPT2 = [ 
    (-120,  230,  20), 
    (-220,   80,  20), 
    (-220,  -80,  20),
    (-120, -230,  20), 
    ( 120, -230,  20),
    ( 220,  -80,  20),
    ( 220,   80,  20),
    ( 120,  230,  20),
    (   0,    0,  20),
]

# BASE WAYPOINTS COORD LIST OPT 2, BUT |+100| ON X AND Y
BASE_WAYPOINTS_COORD_LIST_OPT3 = [ 
    (-220,  330,  20), 
    (-320,  180,  20), 
    (-320, -180,  20),
    (-220, -330,  20), 
    ( 220, -330,  20),
    ( 320, -180,  20),
    ( 320,  180,  20),
    ( 220,  330,  20),
    (   0,    0,  20),
]
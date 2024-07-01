MAX_NODES = 3
SIMULATION_DURATION = 60
SIMULATION_RANGE_X = (-400, 400)
SIMULATION_RANGE_Y = (-400, 400)
SIMULATION_RANGE_Z = (0, 150)
COMMUNICATION_MEDIUM_RANGE = 30
GROUND_BASE_CORD = (0, 0, 0)
RESTART_COORD = (0, 0, 20)
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
    (   0,  200,  20), # waypoint 1
    (-150,  200,  20), # waypoint 2
    (-250,   50,  20), # waypoint 3
    (-250,  -50,  20), # waypoint 4
    (-150, -200,  20), # waypoint 5
    (   0, -200,  20), # waypoint 6
    ( 150, -200,  20), # waypoint 7
    ( 250,  -50,  20), # waypoint 8
    ( 250,   50,  20), # waypoint 9
    ( 150,  200,  20), # waypoint 10
    (   0,  200,  20), # waypoint 1
    RESTART_COORD, # restart coord
]
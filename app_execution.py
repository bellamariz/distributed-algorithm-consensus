from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler, VisualizationConfiguration
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from app_protocol import SensorProtocol, UAVProtocol, GroundStationProtocol

import globals

def main():
    # Configuring simulation
    config = SimulationConfiguration(
        duration=globals.SIMULATION_DURATION,
        real_time=True,
        log_file=f"logs-nodes{globals.MAX_NODES}-dur{globals.SIMULATION_DURATION}.txt",
        execution_logging=True,
    )

    builder = SimulationBuilder(config)

    # Instantiating ground station at a fixed position, ID = 0
    builder.add_node(GroundStationProtocol, globals.GROUND_BASE_CORD)

    # Instantiating UAVs at ground base, IDs = 1,2,3... --> (1, MAX_NODES)
    for _ in range(globals.MAX_NODES):
        builder.add_node(UAVProtocol, globals.GROUND_BASE_CORD)

    # Instantiating sensors in fixed positions, IDs = ... 4,5,6,7,8,9,10,11 -> (MAX_NODES + 1, MAX_NODES + len(SENSORS_COORD_LIST))
    for coord in globals.SENSORS_COORD_LIST:
        builder.add_node(SensorProtocol, coord)

    # Adding required handlers
    builder.add_handler(TimerHandler())
    builder.add_handler(CommunicationHandler(CommunicationMedium(
        transmission_range=globals.COMMUNICATION_MEDIUM_RANGE
    )))
    builder.add_handler(MobilityHandler())
    builder.add_handler(VisualizationHandler(VisualizationConfiguration(
        x_range=globals.SIMULATION_RANGE_X,
        y_range=globals.SIMULATION_RANGE_Y,
        z_range=globals.SIMULATION_RANGE_Z,
    )))

    # Building and starting
    simulation = builder.build()
    simulation.start_simulation()


if __name__ == "__main__":
    main()

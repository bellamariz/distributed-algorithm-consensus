from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler, VisualizationConfiguration
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from app_protocol import SensorProtocol, UAVProtocol, GroundStationProtocol

import globals
import logging

def main():
    _mainLog = logging.getLogger()

    # Configuring simulation
    config = SimulationConfiguration(
        duration=100,
        real_time=True,
        execution_logging=True,
    )

    builder = SimulationBuilder(config)

    # Instantiating sensors in fixed positions
    for coord in globals.SENSORS_COORD_LIST:
        id = builder.add_node(SensorProtocol, coord)
        _mainLog.info(f"Placing sensor {id} at pos {coord}\n")

    # Instantiating ground station at a fixed position
    builder.add_node(GroundStationProtocol, globals.GROUND_BASE_CORD)
    _mainLog.info(f"Placing ground station at pos {globals.GROUND_BASE_CORD}\n")

    # Instantiating UAVs at ground base
    for _ in range(globals.MAX_NODES - 1):
        id = builder.add_node(UAVProtocol, globals.GROUND_BASE_CORD)
        _mainLog.info(f"Placing UAV {id} at ground station\n")

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

import enum
import json
import logging
from typing import TypedDict
import globals
import random

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.communication import SendMessageCommand, BroadcastMessageCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.plugin.mission_mobility import MissionMobilityPlugin, MissionMobilityConfiguration, LoopMission

## Generalized message format to faciliate serialization that has fields necessary for all commuications
class GeneralMessage(TypedDict):
    total_packets: int
    sender_type: int
    sender_id: int

## Maps to GeneralMessage sender type
class GeneralSender(enum.Enum):
    GROUND_STATION = 0
    SENSOR = 1
    UAV = 2

## Auxiliary methods

def report_message(message: GeneralMessage) -> str:
    return (f"Received message with {message['total_packets']} packets from "
            f"{GeneralSender(message['sender_type']).name} {message['sender_id']}")

def new_message(packets: int, senderType: int, senderID: int) -> GeneralMessage:
    message: GeneralMessage = {
        'total_packets': packets,
        'sender_type': senderType,
        'sender_id': senderID,
    }

    return message


## Protocols

## Implementation for the sensor
class SensorProtocol(IProtocol):
    _log: logging.Logger
    total_stored_packets: int

    def initialize(self) -> None:
        self._log = logging.getLogger()
        self.total_stored_packets = 0

        self._generate_packet()

    # Generate a packet every one second using a timer
    def _generate_packet(self) -> None:
        self.total_stored_packets += 1
        self._log.info(f"Generated packet, current count {self.total_stored_packets}")
        self.provider.schedule_timer("sensor_generate_packet", self.provider.current_time() + 1)

    # Sensor implements handle_timer
    def handle_timer(self, timer: str) -> None:
        if (timer == "sensor_generate_packet"):
            self._generate_packet()
    
    # Sensor implements handle_packets
    def handle_packet(self, message: str) -> None:
        general_message: GeneralMessage = json.loads(message)
        self._log.info(report_message(general_message))

        # Sensor receives a message from UAV and sends all its packets to UAV
        if general_message["sender_type"] == GeneralSender.UAV.value:
            responseToUAV = new_message(
                packets=self.total_stored_packets,
                senderType= GeneralSender.SENSOR.value,
                senderID=self.provider.get_id(),
            )

            responseCmd = SendMessageCommand(json.dumps(responseToUAV), general_message["sender_id"])
            self.provider.send_communication_command(responseCmd)

            self._log.info(f"Sent {responseToUAV['total_packets']} packets to UAV {general_message['sender_id']}")

            self.total_stored_packets = 0

    # Sensor implements handle_telemetry
    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    # Sensor implements finish
    def finish(self) -> None:
        self._log.info(f"Final packet count: {self.total_stored_packets}")



## Implementation for the ground station
class GroundStationProtocol(IProtocol):
    _log: logging.Logger
    total_collected_packets: int

    def initialize(self) -> None:
        self._log = logging.getLogger()
        self.total_collected_packets = 0

    # GroundStation implements handle_timer
    def handle_timer(self, timer: str) -> None:
        pass

    # GroundStation implements handle_packet
    def handle_packet(self, message: str) -> None:
        general_message: GeneralMessage = json.loads(message)
        self._log.info(report_message(general_message))

         # GroundStation receives a message from UAV and collects all packets from it
        if general_message["sender_type"] == GeneralSender.UAV.value:
            responseToUAV = new_message(
                packets=self.total_collected_packets,
                senderType= GeneralSender.GROUND_STATION.value,
                senderID=self.provider.get_id(),
            )

            responseCmd = SendMessageCommand(json.dumps(responseToUAV), general_message["sender_id"])
            self.provider.send_communication_command(responseCmd)

            self._log.info(f"Sent acknowledgment to UAV {general_message['sender_id']}. Current count {self.total_collected_packets}")

    # GroundStation implements handle_telemetry
    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    # GroundStation implements finish
    def finish(self) -> None:
        self._log.info(f"Final packet count: {self.total_collected_packets}")



## Implementation for the UAV
class UAVProtocol(IProtocol):
    _log: logging.Logger
    total_received_packets: int
    waypoints: list
    _mission: MissionMobilityPlugin

    def initialize(self) -> None:
        self._log = logging.getLogger()
        self.total_received_packets = 0
        self._mission = MissionMobilityPlugin(self, MissionMobilityConfiguration(
            speed=100,
        ))

        self._init_waypoints()
        self._mission.start_mission(self.waypoints)
        self._ping_network()

    # Calculate waypoints for each UAV - with offesets so they do not overlap
    def _init_waypoints(self) -> None:
        uavID = self.provider.get_id()
        # offsetFactor = (uavID * random.randint(1, 8))
        baseWaypoints = globals.BASE_WAYPOINTS_COORD_LIST
        uavWaypoints = []

        # Iterate over all base waypoint coords (except last, which is return to base)
        for coord in baseWaypoints[:-1]:
            offsetFactor = (uavID * random.randint(1, 5))
            x = coord[0] + offsetFactor
            y = coord[1] - offsetFactor
            z = coord[2]
            uavWaypoints.append((x,y,z))

        uavWaypoints.append(baseWaypoints[-1])
        self.waypoints = uavWaypoints.copy()
        self._log.info(f"Waypoints for uav {uavID}: {self.waypoints}")

    # UAV will ping network (send broadcast) every one second using a timer
    def _ping_network(self) -> None:
        self._log.info(f"Pinging network, current packet count {self.total_received_packets}")

        messageToAll = new_message(
            packets=self.total_received_packets,
            senderType= GeneralSender.UAV.value,
            senderID=self.provider.get_id(),
        )

        broadcastCmd = BroadcastMessageCommand(json.dumps(messageToAll))
        self.provider.send_communication_command(broadcastCmd)

        self.provider.schedule_timer("uav_ping_network", self.provider.current_time() + 1)
    
    # UAV implements handle_timer
    def handle_timer(self, timer: str) -> None:
        if (timer == "uav_ping_network"):
            self._ping_network()

    # UAV implements handle_packet
    def handle_packet(self, message: str) -> None:
        general_message: GeneralMessage = json.loads(message)
        self._log.info(report_message(general_message))

        if general_message["sender_type"] == GeneralSender.SENSOR.value:
            self.total_received_packets += general_message["total_packets"]
            self._log.info(f"Received {general_message['total_packets']} packets from "
                           f"sensor {general_message['sender_id']}. Current count {self.total_received_packets}.")
        elif general_message["sender_type"] == GeneralSender.GROUND_STATION.value:
            self.total_received_packets = 0
            self._log.info("Received acknowledgment from ground station")
    
    # UAV implements handle_telemetry
    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    # UAV implements finish
    def finish(self) -> None:
        self._log.info(f"Final packet count: {self.total_received_packets}")



## TODO: Implementation for the consensus
## TODO: If UAV is closest to Sensor, it will receive its packets
class ConsensusProtocol(IProtocol):
    _log: logging.Logger
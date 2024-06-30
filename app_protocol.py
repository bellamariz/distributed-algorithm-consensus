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

## Auxiliary methods for logging
def report_message(message: GeneralMessage) -> str:
    return (f"Received message with {message['total_packets']} packets from "
            f"{GeneralSender(message['sender_type']).name} {message['sender_id']}")


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
        self.provider.schedule_timer("generate_packet", self.provider.current_time() + 1)

    # Sensor implements handle_timer
    def handle_timer(self, timer: str) -> None:
        if (timer == "generate_packet"):
            self._generate_packet()
    
    # Sensor implements handle_packets
    def handle_packet(self, message: str) -> None:
        general_message: GeneralMessage = json.loads(message)
        self._log(report_message(general_message))

        # Sensor receives a message from UAV and dumps all packets to UAV
        if general_message["sender_type"] == GeneralSender.UAV.value:
            resposeToUAV: GeneralMessage = {
                'total_packets': self.total_stored_packets,
                'sender_type': GeneralSender.SENSOR.value,
                'sender_id': self.provider.get_id()
            }

            responseCmd = SendMessageCommand(json.dumps(resposeToUAV), general_message["sender_id"])
            self.provider.send_communication_command(responseCmd)

            self._log.info(f"Sent {resposeToUAV['total_packets']} packets to UAV {general_message['sender_id']}")

            self.total_stored_packets = 0

    # Sensor implements handle_telemetry
    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    # Sensor implements finish
    def finish(self) -> None:
        self._log.info(f"Final packet count: {self.packet_count}")



## Implementation for the ground station
class GroundStationProtocol(IProtocol):
    _log: logging.Logger
    total_received_packets: int

    def initialize(self) -> None:
        self._log = logging.getLogger()
        self.total_received_packets = 0

    # GroundStation implements handle_timer
    def handle_timer(self, timer: str) -> None:
        pass

    # GroundStation implements handle_packet
    def handle_packet(self, message: str) -> None:
        general_message: GeneralMessage = json.loads(message)
        self._log(report_message(general_message))

         # GroundStation receives a message from UAV and dumps all packets to UAV
        if general_message["sender_type"] == GeneralSender.UAV.value:
            resposeToUAV: GeneralMessage = {
                'total_packets': self.total_received_packets,
                'sender_type': GeneralSender.GROUND_STATION.value,
                'sender_id': self.provider.get_id()
            }

            responseCmd = SendMessageCommand(json.dumps(resposeToUAV), general_message["sender_id"])
            self.provider.send_communication_command(responseCmd)

            self._log.info(f"Sent acknowledgment to UAV {general_message['sender_id']}. Current count {self.total_received_packets}")

    # GroundStation implements handle_telemetry
    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    # GroundStation implements finish
    def finish(self) -> None:
        self._log.info(f"Final packet count: {self.total_received_packets}")



## TODO: Implementation for the UAV
class UAVProtocol(IProtocol):
    _log: logging.Logger

## TODO: Implementation for the consensus
class ConsensusProtocol(IProtocol):
    _log: logging.Logger
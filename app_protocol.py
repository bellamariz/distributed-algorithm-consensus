import enum
import json
import logging
from typing import TypedDict
import globals
import random

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.communication import SendMessageCommand, BroadcastMessageCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.position import *
from gradysim.protocol.plugin.mission_mobility import MissionMobilityPlugin, MissionMobilityConfiguration, GotoCoordsMobilityCommand

## Generalized message format to faciliate serialization that has fields necessary for all commuications
class GeneralMessage(TypedDict):
    total_packets: int
    sender_type: int
    sender_id: int
    sender_pos: Position
    proposal: tuple
    decision: int
    pause_network: bool

## Maps to GeneralMessage sender type
class GeneralSender(enum.Enum):
    GROUND_STATION = 0
    SENSOR = 1
    UAV = 2

## Auxiliary methods

def report_message(message: GeneralMessage) -> str:
    return (f"Received message with {message['total_packets']} packets from "
            f"{GeneralSender(message['sender_type']).name} {message['sender_id']}")

def new_message(packets: int, senderType: int, senderID: int, senderPos: Position, proposal: tuple = (-1, 0), decision: int = -1, pause: bool = False) -> GeneralMessage:
    message: GeneralMessage = {
        'total_packets': packets,
        'sender_type': senderType,
        'sender_id': senderID,
        'sender_pos': senderPos,
        'proposal': proposal,
        'decision': decision,
        'pause_network': pause,
    }

    return message

def get_uav_distances_from_sensor(uavPos: dict, sensorPos: Position) -> dict:
    uavDists = dict()

    for uav, pos in uavPos.items():
        distFromSensor = squared_distance(tuple(pos), sensorPos)
        uavDists.update({int(uav) : round(distFromSensor, 5)})

    return uavDists

# If MAX_NODES = 3, IDs will be [1, 2, 3]
def get_uav_ids() -> list:
    return list(range(1, globals.MAX_NODES+1))

# Consensus coordinating host will be UAV with biggest ID
def get_coordinating_host() -> int:
    return max(get_uav_ids())

def total_uavs() -> int:
    return len(get_uav_ids())

# { 1 : (2, 121.55), 2 : (2, 120.99), 3 : (1, 130.25) }
# min would be value (2, 120.99) - smallest distance
def make_decision(proposals: dict) -> tuple:
    key = min(proposals, key=lambda x: proposals[x][1])
    return tuple(proposals.get(key))

## Protocols

## Implementation for the sensor
class SensorProtocol(IProtocol):
    _log: logging.Logger
    total_stored_packets: int
    position: Position
    _id: int

    def initialize(self) -> None:
        self._log = logging.getLogger()
        self._id = self.provider.get_id()
        self.total_stored_packets = 0
        self.position = globals.SENSORS_COORD_LIST[self._id - globals.MAX_NODES - 1]

        self._generate_packet()

    # Generate a packet every three seconds using a timer
    def _generate_packet(self) -> None:
        self.total_stored_packets += 1
        self.provider.schedule_timer("sensor_generate_packet", self.provider.current_time() + 1)
        # self._log.info(f"Generated packet, current count {self.total_stored_packets}")

    # Sensor implements handle_timer
    def handle_timer(self, timer: str) -> None:
        if (timer == "sensor_generate_packet"):
            self._generate_packet()
    
    # Sensor implements handle_packets
    def handle_packet(self, message: str) -> None:
        general_message: GeneralMessage = json.loads(message)
        # self._log.info(report_message(general_message))

        # Sensor receives a message from UAV
        if general_message["sender_type"] == GeneralSender.UAV.value:

            #If UAVs made a decision as to who will receive packets
            if(general_message["decision"]) >= 0:
                responseToUAV = new_message(
                    packets=self.total_stored_packets,
                    senderType= GeneralSender.SENSOR.value,
                    senderID=self._id,
                    senderPos=self.position,
                    decision=general_message["decision"],
                )

                responseCmd = SendMessageCommand(json.dumps(responseToUAV), general_message["decision"])
                self.provider.send_communication_command(responseCmd)

                self.total_stored_packets = 0
                
                self._log.info(f"Sensor sent {responseToUAV['total_packets']} packets to UAV {general_message['decision']}")
            else:
                responseToUAV = new_message(
                    packets=0,
                    senderType= GeneralSender.SENSOR.value,
                    senderID=self._id,
                    senderPos=self.position,
                )

                responseCmd = SendMessageCommand(json.dumps(responseToUAV), general_message["sender_id"])
                self.provider.send_communication_command(responseCmd)

                self._log.info(f"Sensor sent coordinates to UAV {general_message['sender_id']}")


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
    position: Position
    _id: int

    def initialize(self) -> None:
        self._log = logging.getLogger()
        self._id = self.provider.get_id()
        self.total_collected_packets = 0
        self.position = globals.GROUND_BASE_CORD

    # GroundStation implements handle_timer
    def handle_timer(self, timer: str) -> None:
        pass

    # GroundStation implements handle_packet
    def handle_packet(self, message: str) -> None:
        general_message: GeneralMessage = json.loads(message)
        # self._log.info(report_message(general_message))

         # GroundStation receives a message from UAV and collects all packets from it
        if general_message["sender_type"] == GeneralSender.UAV.value:
            responseToUAV = new_message(
                packets=self.total_collected_packets,
                senderType= GeneralSender.GROUND_STATION.value,
                senderID=self._id,
                senderPos=self.position,
            )

            responseCmd = SendMessageCommand(json.dumps(responseToUAV), general_message["sender_id"])
            self.provider.send_communication_command(responseCmd)

            self.total_collected_packets += general_message["total_packets"]

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
    position: Position
    uavPositions: dict
    _id: int
    _coordHost: int
    paused: bool
    currentWaypointIndex: int
    proposals = dict

    def initialize(self) -> None:
        self._log = logging.getLogger()
        self.currentWaypointIndex = 0
        self.uavPositions = dict()
        self.proposals = dict()
        self._id = self.provider.get_id()
        self._coordHost = get_coordinating_host()
        self._mission = MissionMobilityPlugin(self, MissionMobilityConfiguration(
            speed=100,
        ))

        self._start_routine()

    # Start new routine
    def _start_routine(self) -> None:
        self._paused = False
        self.total_received_packets = 0
        self.position = globals.GROUND_BASE_CORD
        self.proposals.clear()
        self.uavPositions.clear()
        self.uavPositions.update({self._id : self.position})

        # Start new mission if there was none before
        if(self._mission.is_idle):
            self._init_waypoints()
            self._mission.start_mission(self.waypoints)
            self._ping_network()

    # Calculate waypoints for each UAV - with random offesets so they do not overlap
    def _init_waypoints(self) -> None:
        baseWaypoints = globals.BASE_WAYPOINTS_COORD_LIST
        uavWaypoints = []
        midPoint = len(baseWaypoints)//2

        # Iterate over all base waypoint coords (except last, which is return to base)
        for coord in baseWaypoints[:midPoint]:
            offsetFactor = (self._id * random.randint(3, 7))
            x = coord[0] - offsetFactor
            y = coord[1] - offsetFactor
            z = coord[2]
            uavWaypoints.append((x,y,z))

        for coord in baseWaypoints[midPoint:-1]:
            offsetFactor = (self._id * random.randint(3, 7))
            x = coord[0] + offsetFactor
            y = coord[1] + offsetFactor
            z = coord[2]
            uavWaypoints.append((x,y,z))

        uavWaypoints.append(baseWaypoints[-1])
        self.waypoints = uavWaypoints.copy()
        self._log.info(f"Waypoints for uav: {self.waypoints}")

    # UAV will ping network (send broadcast) every 1 second using a timer
    def _ping_network(self) -> None:
        self._log.info(f"Paused: {self._paused}")
        # If paused for consensus, do nothing else
        if (self._paused):
            return

        messageToAll = new_message(
            packets=self.total_received_packets,
            senderType= GeneralSender.UAV.value,
            senderID=self._id,
            senderPos=self.position,
        )

        broadcastCmd = BroadcastMessageCommand(json.dumps(messageToAll))
        self.provider.send_communication_command(broadcastCmd)

        self._log.info(f"Pinging network, current packet count {self.total_received_packets}")

        self.provider.schedule_timer("uav_ping_network", self.provider.current_time() + 1)

    # If UAV is not already paused, coord will send a broadcast so they stop moving until consensus is finished
    def _pause_network(self) -> None:
        messageToAll = new_message(
            packets=self.total_received_packets,
            senderType= GeneralSender.UAV.value,
            senderID=self._id,
            senderPos=self.position,
            pause=True,
        )

        broadcastCmd = BroadcastMessageCommand(json.dumps(messageToAll))
        self.provider.send_communication_command(broadcastCmd)

    # Broadcast decision for all nodes
    def _broadcast_decision(self, decision: int) -> None:
        messageToAll = new_message(
            packets=self.total_received_packets,
            senderType= GeneralSender.UAV.value,
            senderID=self._id,
            senderPos=self.position,
            decision=decision,
        )

        broadcastCmd = BroadcastMessageCommand(json.dumps(messageToAll))
        self.provider.send_communication_command(broadcastCmd)

    # UAV will send broadcast with proposed consensus value to coordinating host
    def _send_proposal_to_coord_host(self, uavProposal: tuple) -> None:
        proposalMsg = new_message(
            packets=self.total_received_packets,
            senderType= GeneralSender.UAV.value,
            senderID=self._id,
            senderPos=self.position,
            proposal=uavProposal,
        )

        proposalCmd = SendMessageCommand(json.dumps(proposalMsg), self._coordHost)
        self.provider.send_communication_command(proposalCmd)
    
    # Organize consensus to see who will reach the sensor
    def _organize_consensus(self, msg: GeneralMessage) -> None:
        # Received message from sensor
        if msg["sender_type"] == GeneralSender.SENSOR.value:
            # A decision was made on what UAV will collect packets from sensor
            if msg["decision"] >= 0:
                # This UAV was chosen to go to sensor and collect data
                if msg["decision"] == self._id:
                    if self._paused:
                        # Receive packets
                        self.total_received_packets += msg["total_packets"]
                        self._log.info(f"Received {msg['total_packets']} packets from sensor {msg['sender_id']}. Current count {self.total_received_packets}.")
                        self.provider.schedule_timer("wait_until_packets_received", self.provider.current_time() + 3)

            else: # This UAV received coordinates from sensor and will calculate distances from it
                if (self._coordHost != self._id):
                    if not self._paused:
                        uavDistsFromSensor = get_uav_distances_from_sensor(self.uavPositions, msg["sender_pos"])
                        minUAV = min(uavDistsFromSensor, key=uavDistsFromSensor.get)
                        minDist = uavDistsFromSensor.get(minUAV)
                        self._send_proposal_to_coord_host((minUAV, minDist))

                        self._log.info(f"Sent proposal to coordinating host")

                        self._paused = True
                        self.currentWaypointIndex = self._mission.current_waypoint
                        self._mission.stop_mission()

                        self._log.info(f"Pausing mobility due to consensus")
                

        # Received message from other UAVs
        elif msg["sender_type"] == GeneralSender.UAV.value:
            # Received ping_network
            if (msg["decision"] < 0) and (msg["proposal"][0] < 0):
                if not self._paused:
                    self.uavPositions.update({msg["sender_id"] : msg["sender_pos"]})
            
            # Need to make a decision about what UAV will go to sensor based on received proposals
            elif (msg["decision"] < 0) and (msg["proposal"][0] >= 0):
                # If uav is coordinating host, enter consensus mode and pause movimentation of network
                if (self._coordHost == self._id):
                    if not self._paused:
                        self._log.info(f"Coordinating host pausing network and starting consensus")

                        self._paused = True
                        self.currentWaypointIndex = self._mission.current_waypoint
                        self._mission.stop_mission()
                        self._pause_network()
                        self.provider.schedule_timer("coord_waiting_for_proposal", self.provider.current_time() + 3)
                    # For each received proposal, we have a dict: { proposer_uav_id : (proposed_uav, proposed_dist) }
                    self.proposals.update({msg["sender_id"] : msg["proposal"]})
            
            # UAV stop moving until consensus finishes
            elif msg["pause_network"]:
                if msg["sender_id"] == self._coordHost:
                    if not self._paused:
                        self._paused = True
                        self.currentWaypointIndex = self._mission.current_waypoint
                        self._mission.stop_mission()

                        self._log.info(f"Pausing mobility due to consensus")
            
            # After consensus finishes
            elif (msg["decision"] >= 0):
                # If UAV was waiting for consensus
                if self._paused:
                    # If this UAV was the decision
                    if (msg["decision"] == self._id):
                        self._broadcast_decision(msg["decision"])
                    else:
                        # If the decision was not the coordinating host
                        if (msg["decision"] != self._coordHost):
                            # Resume mobility
                            self._paused = False
                            lastWaypoint = self.currentWaypointIndex
                            self._mission.start_mission(self.waypoints[lastWaypoint:])
                        else:
                            self.provider.schedule_timer("wait_until_packets_received", self.provider.current_time() + 3)

                            

    # UAV implements handle_timer
    def handle_timer(self, timer: str) -> None:
        if (timer == "uav_ping_network"):
            self._ping_network()
        elif (timer == "restart_mission"):
            self._log.info(f"Restarting mission for uav")
            self._start_routine()
        elif (timer == "wait_until_packets_received"):
            # Resume mobility
            self._paused = False
            lastWaypoint = self.currentWaypointIndex
            self._mission.start_mission(self.waypoints[lastWaypoint:])
        elif (timer == "coord_waiting_for_proposal"):
            # Coord host calculates final decision
            self._log.info(f"Proposals for consensus: {self.proposals}")
            finalDecision = make_decision(self.proposals)
            self._log.info(f"Decision for consensus: {finalDecision}")

            # Broadcast decision
            self._broadcast_decision(finalDecision[0])
            self.proposals.clear()

            # Resume mobility
            if (finalDecision[0] != self._id):
                self._paused = False
                lastWaypoint = self.currentWaypointIndex
                self._mission.start_mission(self.waypoints[lastWaypoint:])


    # UAV implements handle_packet
    def handle_packet(self, message: str) -> None:
        general_message: GeneralMessage = json.loads(message)
        # self._log.info(report_message(general_message))

        if general_message["sender_type"] == GeneralSender.GROUND_STATION.value:
            self.total_received_packets = 0
        else:
            self._organize_consensus(general_message)
            
    # UAV implements handle_telemetry
    def handle_telemetry(self, telemetry: Telemetry) -> None:
        if not self._paused:
            self.position = telemetry.current_position
            self.uavPositions.update({self._id : self.position})
            # self._log.info(f"Dict for uav: {self.uavPositions}")

        # If reached end of mission at RESTART_COORD, move back to GROUND_BASE_COORD and start a timer for new mission
        if(telemetry.current_position == globals.RESTART_COORD):
            self._ping_network()
            
            mobilityCmd = GotoCoordsMobilityCommand(
                x=globals.GROUND_BASE_CORD[0],
                y=globals.GROUND_BASE_CORD[0],
                z=globals.GROUND_BASE_CORD[0],
            )
            self.provider.send_mobility_command(mobilityCmd)
            self.provider.schedule_timer("restart_mission", self.provider.current_time() + 5)

    # UAV implements finish
    def finish(self) -> None:
        self._log.info(f"Final packet count: {self.total_received_packets}")
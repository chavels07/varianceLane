# -*- coding: utf-8 -*-
# @Time        : 2023/4/12 15:37
# @File        : sim.py
# @Description :

from collections import namedtuple
from typing import Tuple, List

import traci
import sumolib

from lib.tool import logger
from lib.SPAT import Direction, Turn

# 和VMS的major相对应
VARIANCE_LANE_SCHEME = {
    (True, True): 0,
    (False, True): 1,
    (True, False): 2,
    (False, False): 3
}

DISALLOWED_VEH_TYPE = {
    (True, True): [('-gneE1_0', None), ('-gneE1_1', 'custom1'), ('-gneE0_2', 'custom1')],
    (False, True): [('-gneE1_0', 'custom1'), ('-gneE1_1', 'passenger'), ('-gneE0_2', 'custom1')],
    (True, False): [('-gneE1_0', None), ('-gneE1_1', 'custom1'), ('-gneE0_2', 'passenger')],
    (False, False): [('-gneE1_0', 'custom1'), ('-gneE1_1', 'passenger'), ('-gneE0_2', 'passenger')]
}

LaneScheme = namedtuple('LaneScheme', ['time_sec', 'east_major', 'west_major'])


def allowed_from_disallowed(veh_type):
    if veh_type is None:
        return 'passenger', 'custom1'
    return 'passenger' if veh_type == 'custom1' else 'custom1'


def sim_loop(fixed_plan: List[LaneScheme], junction: str = 'gneJ0'):
    traci.trafficlight.setProgram(junction, 2)
    last_disallowed_check_time = -1
    scheme = None
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep(0)
        current_time = traci.simulation.getTime()
        if last_disallowed_check_time > 0 and current_time >= last_disallowed_check_time + 5:
            program_id = VARIANCE_LANE_SCHEME[scheme.east_major, scheme.west_major]
            for lane_id, disallowed_veh_type in DISALLOWED_VEH_TYPE[scheme.east_major, scheme.west_major]:
                if disallowed_veh_type is not None:
                    traci.lane.setDisallowed(lane_id, disallowed_veh_type)
                    all_veh_current = traci.lane.getLastStepVehicleIDs(lane_id)
                    for veh_id in all_veh_current:
                        if traci.vehicle.getVehicleClass(veh_id) == disallowed_veh_type:
                            traci.vehicle.remove(veh_id)
            last_disallowed_check_time = -1
        if len(fixed_plan):
            if current_time >= fixed_plan[0].time_sec:

                traci.lane.setDisallowed('-gneE0_2', 'custom1')
                scheme = fixed_plan.pop(0)
                program_id = VARIANCE_LANE_SCHEME[scheme.east_major, scheme.west_major]
                for lane_id, disallowed_veh_type in DISALLOWED_VEH_TYPE[scheme.east_major, scheme.west_major]:
                    if disallowed_veh_type is not None:
                        traci.lane.setDisallowed(lane_id, disallowed_veh_type)
                        all_veh_current = traci.lane.getLastStepVehicleIDs(lane_id)
                        for veh_id in all_veh_current:
                            if traci.vehicle.getVehicleClass(veh_id) == disallowed_veh_type:
                                traci.vehicle.remove(veh_id)

                    allowed_veh_type = allowed_from_disallowed(disallowed_veh_type)
                    if isinstance(allowed_veh_type, tuple):
                        for _veh_type in allowed_veh_type:
                            traci.lane.setAllowed(lane_id, _veh_type)
                    traci.lane.setAllowed(lane_id, allowed_veh_type)

                last_disallowed_check_time = current_time
                traci.trafficlight.setProgram(junction, program_id)
                logger.info(f'traffic light change, program id: {program_id}')


def main():
    sumo_cfg_path = 'network/1.sumocfg'
    sumoBinary = sumolib.checkBinary('sumo-gui')
    sumoCmd = [sumoBinary, '-c', sumo_cfg_path]
    traci.start(sumoCmd)
    plan = [LaneScheme(10, True, True), LaneScheme(5940, False, True), LaneScheme(6390, True, True)]
    # plan = [LaneScheme(10, True, True), LaneScheme(6120, False, True), LaneScheme(7200, True, True)]  # current
    sim_loop(plan)


if __name__ == '__main__':
    main()
# -*- coding: utf-8 -*-
# @Time        : 2023/4/10 15:46
# @File        : main.py
# @Description :

from lib.SPAT import Movement, Direction, Turn
from lib.state import TurnDemand
from src.lane_change import DynamicIntersectionController, VarianceLane, LaneAllocation, VMS
from process import read_file


STRAIGHT_SAT_RATE = 1600
TURN_SAT_RATE = 900
LEFT_SAT_RATE = 1300
RIGHT_SAT_RATE = 1400

if __name__ == '__main__':
    LANE_MOVEMENT_MAPPING = {
        16: Movement(Direction.EAST, Turn.STRAIGHT),
        17: Movement(Direction.EAST, Turn.STRAIGHT),
        18: Movement(Direction.EAST, Turn.STRAIGHT),
        19: Movement(Direction.EAST, Turn.RIGHT_TURN),
        30: Movement(Direction.WEST, Turn.LEFT),
        31: Movement(Direction.WEST, Turn.STRAIGHT),
        32: Movement(Direction.WEST, Turn.STRAIGHT),
        33: Movement(Direction.WEST, Turn.STRAIGHT)
    }

    PEAK_LANE_MOVEMENT_MAPPING = {
        16: Movement(Direction.EAST, Turn.STRAIGHT),
        17: Movement(Direction.EAST, Turn.STRAIGHT),
        18: Movement(Direction.EAST, Turn.TURN),
        19: Movement(Direction.EAST, Turn.RIGHT),
        30: Movement(Direction.WEST, Turn.LEFT),
        31: Movement(Direction.WEST, Turn.STRAIGHT),
        32: Movement(Direction.WEST, Turn.STRAIGHT),
        33: Movement(Direction.WEST, Turn.STRAIGHT)
    }

    SAT_THRESHOLD = {
        Turn.LEFT: 0.8,
        Turn.STRAIGHT: 0.75,
        Turn.RIGHT: 0.9,
        Turn.TURN: 0.75
    }

    # east_basic_lane_allocation = {Turn.STRAIGHT: 2, Turn.TURN: 0, Turn.RIGHT: 0}
    # east_flexible_lane_allocation = [
    #     {
    #         Turn.STRAIGHT: 1,
    #         Turn.TURN: 0.5,
    #         Turn.RIGHT: 0.5
    #     },
    #     {
    #         Turn.STRAIGHT: 0,
    #         Turn.TURN: 1,
    #         Turn.RIGHT: 1
    #     }
    # ]
    # east_lane_allocation = LaneAllocation(east_basic_lane_allocation, east_flexible_lane_allocation)
    #
    # west_basic_lane_allocation = {Turn.STRAIGHT: 2, Turn.LEFT: 1}
    # west_flexible_lane_allocation = [
    #     {
    #         Turn.STRAIGHT: 1,
    #         Turn.LEFT: 0,
    #     },
    #     {
    #         Turn.STRAIGHT: 0,
    #         Turn.LEFT: 1
    #     }
    # ]
    # west_lane_allocation = LaneAllocation(west_basic_lane_allocation, west_flexible_lane_allocation)
    #
    # cycle_length = 150
    # east_green_spilt = {Turn.STRAIGHT: 45 / cycle_length, Turn.TURN: 52 / cycle_length, Turn.RIGHT: 1.}
    # west_green_spilt = {Turn.STRAIGHT: 45 / cycle_length, Turn.LEFT: 52 / cycle_length}
    #
    # east_vms = VMS(Turn.STRAIGHT, Turn.STRAIGHT, Turn.TURN)
    # # east_vms1 = VMS(Turn.STRAIGHT, Turn.STRAIGHT, Turn.TURN)
    # # east_vms2 = VMS(Turn.RIGHT_TURN, Turn.RIGHT_TURN, Turn.RIGHT)
    # west_vms = VMS(Turn.STRAIGHT, Turn.STRAIGHT, Turn.LEFT)
    #
    # TRUCK_RATE = 0.2
    # PASSENGER_RATE = 1 - TRUCK_RATE
    # VEH_TYPE_FACTOR = (PASSENGER_RATE + 0.5 * TRUCK_RATE)
    # modified_straight_rate = STRAIGHT_SAT_RATE * VEH_TYPE_FACTOR
    # modified_left_rate = LEFT_SAT_RATE * VEH_TYPE_FACTOR
    # modified_turn_rate = TURN_SAT_RATE * VEH_TYPE_FACTOR
    # modified_right_rate = RIGHT_SAT_RATE * VEH_TYPE_FACTOR
    # east_demand = [TurnDemand(Turn.STRAIGHT, modified_straight_rate), TurnDemand(Turn.TURN, modified_turn_rate),
    #                TurnDemand(Turn.RIGHT, modified_right_rate)]
    # west_demand = [TurnDemand(Turn.STRAIGHT, modified_straight_rate), TurnDemand(Turn.LEFT, modified_left_rate)]
    #
    # v_lane_east = VarianceLane(Direction.EAST, east_vms, SAT_THRESHOLD, east_demand, east_lane_allocation,
    #                            east_green_spilt)
    # v_lane_west = VarianceLane(Direction.WEST, west_vms, SAT_THRESHOLD, west_demand, west_lane_allocation,
    #                            west_green_spilt)
    #
    # controller = DynamicIntersectionController(variance_lanes=[v_lane_east, v_lane_west],
    #                                            lane_movement_mapping=LANE_MOVEMENT_MAPPING,
    #                                            update_interval_sec=1800,
    #                                            peak_lane_movement_mapping=PEAK_LANE_MOVEMENT_MAPPING,
    #                                            peak_hour_range=(17, 20))
    #
    # tf_data_path = 'data/TrafficFlow_Logs3.log'
    # for stat in read_file(tf_data_path):
    #     controller.update_from_traffic_flow(stat[0])

    east_basic_lane_allocation = {Turn.STRAIGHT: 2, Turn.TURN: 0, Turn.RIGHT: 0}
    east_flexible_lane_allocation = [
        {
            Turn.STRAIGHT: 1,
            Turn.TURN: 0.5,
            Turn.RIGHT: 1
        },
        {
            Turn.STRAIGHT: 0,
            Turn.TURN: 1,
            Turn.RIGHT: 1
        }
    ]
    east_lane_allocation = LaneAllocation(east_basic_lane_allocation, east_flexible_lane_allocation)

    west_basic_lane_allocation = {Turn.STRAIGHT: 2, Turn.LEFT: 1}
    west_flexible_lane_allocation = [
        {
            Turn.STRAIGHT: 1,
            Turn.LEFT: 0,
        },
        {
            Turn.STRAIGHT: 0,
            Turn.LEFT: 1
        }
    ]
    west_lane_allocation = LaneAllocation(west_basic_lane_allocation, west_flexible_lane_allocation)

    cycle_length = 150
    east_green_spilt = {Turn.STRAIGHT: 45 / cycle_length, Turn.TURN: 52 / cycle_length, Turn.RIGHT: (1., 52 / cycle_length)}
    west_green_spilt = {Turn.STRAIGHT: 45 / cycle_length, Turn.LEFT: 52 / cycle_length}

    east_vms = VMS(Turn.STRAIGHT, Turn.STRAIGHT, Turn.RIGHT)
    # east_vms1 = VMS(Turn.STRAIGHT, Turn.STRAIGHT, Turn.TURN)
    # east_vms2 = VMS(Turn.RIGHT_TURN, Turn.RIGHT_TURN, Turn.RIGHT)
    west_vms = VMS(Turn.STRAIGHT, Turn.STRAIGHT, Turn.LEFT)

    TRUCK_RATE = 0.2
    PASSENGER_RATE = 1 - TRUCK_RATE
    VEH_TYPE_FACTOR = (PASSENGER_RATE + 0.5 * TRUCK_RATE)
    modified_straight_rate = STRAIGHT_SAT_RATE * VEH_TYPE_FACTOR
    modified_left_rate = LEFT_SAT_RATE * VEH_TYPE_FACTOR
    modified_turn_rate = TURN_SAT_RATE * VEH_TYPE_FACTOR
    modified_right_rate = RIGHT_SAT_RATE * VEH_TYPE_FACTOR
    east_demand = [TurnDemand(Turn.STRAIGHT, modified_straight_rate), TurnDemand(Turn.TURN, modified_turn_rate),
                   TurnDemand(Turn.RIGHT, modified_right_rate)]
    west_demand = [TurnDemand(Turn.STRAIGHT, modified_straight_rate), TurnDemand(Turn.LEFT, modified_left_rate)]

    v_lane_east = VarianceLane(Direction.EAST, east_vms, SAT_THRESHOLD, east_demand, east_lane_allocation,
                               east_green_spilt)
    v_lane_west = VarianceLane(Direction.WEST, west_vms, SAT_THRESHOLD, west_demand, west_lane_allocation,
                               west_green_spilt)

    controller = DynamicIntersectionController(variance_lanes=[v_lane_east, v_lane_west],
                                               lane_movement_mapping=LANE_MOVEMENT_MAPPING,
                                               update_interval_sec=1800,
                                               peak_lane_movement_mapping=PEAK_LANE_MOVEMENT_MAPPING,
                                               peak_hour_range=(17, 20))

    tf_data_path = 'data/TrafficFlow_Logs3.log'
    for stat in read_file(tf_data_path):
        controller.update_from_traffic_flow(stat[0])
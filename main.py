# -*- coding: utf-8 -*-
# @Time        : 2023/4/10 15:46
# @File        : main.py
# @Description :
from utils.config import load_json

load_json('setting.json')

from functools import partial

from lib.SPAT import Movement, Direction, Turn
from lib.state import TurnDemand, DayLanePlan, PlanDuration
from src.lane_change import (StaticIntersectionController, DynamicIntersectionController, VarianceLane, LaneAllocation,
                             VMS)
from src.connection import Connection
from utils.process import read_file
from utils.data_load import date_classify_date

STRAIGHT_SAT_RATE = 1600
TURN_SAT_RATE = 900
LEFT_SAT_RATE = 1300
RIGHT_SAT_RATE = 1400

# TODO: East变化太多
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

    # 只有东进口变
    PEAK_LANE_MOVEMENT_MAPPING1 = {
        16: Movement(Direction.EAST, Turn.STRAIGHT),
        17: Movement(Direction.EAST, Turn.STRAIGHT),
        18: Movement(Direction.EAST, Turn.TURN),
        19: Movement(Direction.EAST, Turn.RIGHT),
        30: Movement(Direction.WEST, Turn.LEFT),
        31: Movement(Direction.WEST, Turn.STRAIGHT),
        32: Movement(Direction.WEST, Turn.STRAIGHT),
        33: Movement(Direction.WEST, Turn.STRAIGHT)
    }

    # 两者都变
    PEAK_LANE_MOVEMENT_MAPPING2 = {
        16: Movement(Direction.EAST, Turn.STRAIGHT),
        17: Movement(Direction.EAST, Turn.STRAIGHT),
        18: Movement(Direction.EAST, Turn.TURN),
        19: Movement(Direction.EAST, Turn.RIGHT),
        30: Movement(Direction.WEST, Turn.LEFT),
        31: Movement(Direction.WEST, Turn.LEFT),
        32: Movement(Direction.WEST, Turn.STRAIGHT),
        33: Movement(Direction.WEST, Turn.STRAIGHT)
    }

    # 只有西进口改变
    PEAK_LANE_MOVEMENT_MAPPING3 = {
        16: Movement(Direction.EAST, Turn.STRAIGHT),
        17: Movement(Direction.EAST, Turn.STRAIGHT),
        18: Movement(Direction.EAST, Turn.STRAIGHT),
        19: Movement(Direction.EAST, Turn.RIGHT_TURN),
        30: Movement(Direction.WEST, Turn.LEFT),
        31: Movement(Direction.WEST, Turn.LEFT),
        32: Movement(Direction.WEST, Turn.STRAIGHT),
        33: Movement(Direction.WEST, Turn.STRAIGHT)
    }

    SAT_THRESHOLD = {
        Turn.LEFT: 0.85,
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
    # controller = StaticIntersectionController(variance_lanes=[v_lane_east, v_lane_west],
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
            Turn.RIGHT: 0.5
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
    east_green_spilt = {Turn.STRAIGHT: 45 / cycle_length, Turn.TURN: 52 / cycle_length,
                        Turn.RIGHT: (1., 1 - (1 - 52 / cycle_length) * 0.3)}
    west_green_spilt = {Turn.STRAIGHT: 45 / cycle_length, Turn.LEFT: 52 / cycle_length}


    def east_vms_state_output_func(turn: Turn):
        vms_3 = {'vmsId': 3, 'laneId': 19, 'direction': 2}  # 最右侧
        vms_4 = {'vmsId': 4, 'laneId': 18, 'direction': 2}  # 次右侧

        if turn is Turn.STRAIGHT:
            vms_3['movement'] = 8
            vms_4['movement'] = 1
        elif turn is Turn.RIGHT:
            vms_3['movement'] = 3
            vms_4['movement'] = 4
        else:
            raise NotImplementedError('invalid priority turn for east entry link')
        return [vms_3, vms_4]


    def west_vms_state_output_func(turn: Turn):
        vms_1 = {'vmsId': 1, 'laneId': 31, 'direction': 4}  # 下游
        vms_2 = {'vmsId': 2, 'laneId': 31, 'direction': 4}  # 上游

        if turn is Turn.STRAIGHT:
            vms_1['movement'] = 1
            vms_2['movement'] = 1
        elif turn is Turn.LEFT:
            vms_1['movement'] = 2
            vms_2['movement'] = 2
        else:
            raise NotImplementedError('invalid priority turn for west entry link')
        return [vms_1, vms_2]


    east_vms = VMS(Turn.STRAIGHT, Turn.STRAIGHT, Turn.RIGHT, entity_state_func=east_vms_state_output_func)
    # east_vms1 = VMS(Turn.STRAIGHT, Turn.STRAIGHT, Turn.TURN)
    # east_vms2 = VMS(Turn.RIGHT_TURN, Turn.RIGHT_TURN, Turn.RIGHT)
    west_vms = VMS(Turn.STRAIGHT, Turn.STRAIGHT, Turn.LEFT, entity_state_func=west_vms_state_output_func)

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

    # controller = StaticIntersectionController(variance_lanes=[v_lane_east, v_lane_west],
    #                                           lane_movement_mapping=LANE_MOVEMENT_MAPPING,
    #                                           update_interval_sec=1800,
    #                                           peak_lane_movement_mapping=PEAK_LANE_MOVEMENT_MAPPING,
    #                                           peak_hour_range=(17, 20))
    #
    # tf_data_path = 'data/TrafficFlow_Logs3.log'
    # for stat in read_file(tf_data_path):
    #     controller.update_from_traffic_flow(stat[0])

    peak1_pd = PlanDuration(PEAK_LANE_MOVEMENT_MAPPING3, 8, 10)
    peak2_pd = PlanDuration(PEAK_LANE_MOVEMENT_MAPPING3, 16, 16.5)
    peak3_pd = PlanDuration(PEAK_LANE_MOVEMENT_MAPPING2, 16.5, 19)
    peak4_pd = PlanDuration(PEAK_LANE_MOVEMENT_MAPPING1, 19, 20)

    normal1_pd = PlanDuration(LANE_MOVEMENT_MAPPING, 0, 8)
    normal2_pd = PlanDuration(LANE_MOVEMENT_MAPPING, 10, 16)
    normal3_pd = PlanDuration(LANE_MOVEMENT_MAPPING, 20, 24)
    day_lane_plan = DayLanePlan([peak1_pd, peak2_pd, peak3_pd, peak4_pd, normal1_pd, normal2_pd, normal3_pd])

    assemble_avg_flow = date_classify_date('data/history',
                                           {'weekdays': [4, 6, 7, 10, 11, 12], 'weekends': [8, 9], 'festivals': [5]}, 1,
                                           [16, 17, 18, 19, 30, 31, 32, 33])

    connection = Connection()
    controller = DynamicIntersectionController(variance_lanes=[v_lane_east, v_lane_west],
                                               lane_movement_mapping=LANE_MOVEMENT_MAPPING,
                                               update_interval_sec=1200,  # 1800
                                               history_lane_flow=assemble_avg_flow,
                                               history_lane_movement_mapping=day_lane_plan,
                                               connection=connection)

    # connection.connect(tf_handle=partial(controller.update_from_traffic_flow, publish=True),
    #                    queue_handle=controller.update_from_queue)
    # connection.loop_start()
    tf_data_path = 'data/TrafficFlow_Logs3.log'
    for stat in read_file(tf_data_path):
        controller.update_from_traffic_flow(stat[0], publish=True)

# -*- coding: utf-8 -*-
# @Time        : 2023/4/6 20:21
# @File        : state.py
# @Description :
from typing import List, Dict, Optional, Iterable

from dataclasses import dataclass
from lib.SPAT import Turn, Movement

PRIORITY_FACTOR = {
    1: 1.2,
    2: 1.,
    3: 0.8,
    4: 0.6
}


@dataclass
class TurnDemand:
    turn: Turn
    capacity_hour_per_lane: float
    flow_hour_total: float = 0
    avg_queue_length: float = 0
    priority: Optional[int] = None  # 优先级增序

    def saturation_rate(self, green_spilt: float, lane_num):
        return self.flow_hour_total / (self.capacity_hour_per_lane * lane_num * green_spilt)

    def update(self, flow: float, queue_length: float):
        self.flow_hour_total = flow
        self.avg_queue_length = queue_length


@dataclass
class PlanDuration:
    movement_allocation: Dict[int, Movement]
    hour_start: float
    hour_end: float


class DayLanePlan:
    def __init__(self, plans: List[PlanDuration]):
        self.plans: List[PlanDuration] = self.sorted_plan_duration(plans)  # 按时间排序的车道分配方案

    def sorted_plan_duration(self, plan):
        plan = sorted(plan, key=lambda x: x.hour_start)
        # check overlapping
        for prev_plan, next_plan in zip(plan[:-1], plan[1:]):
            if prev_plan.hour_end > next_plan.hour_start:
                raise ValueError('Overlap in lane allocation plan')
        return plan

    def search_plan(self, hour: float):
        """给定时段寻找对应的车道分配方案"""
        for plan in self.plans:
            if plan.hour_start <= hour < plan.hour_end:
                return plan
        raise ValueError(f'cannot find lane allocation plan for hour {hour}')


class LaneFlowStorage:
    def __init__(self, lanes: Iterable[int]):
        self.flows = {lane: -1 for lane in lanes}

    def get_lane_flow_last_step(self, lane_id: int) -> float:
        return self.flows[lane_id]

    def record_flow(self, lane_id: int, flow: float):
        if lane_id not in self.flows:
            raise ValueError(f'invalid lane id {lane_id}')
        self.flows[lane_id] = flow

    def record_multiple_flow(self, update_flows: Dict[int, float]):
        for lane_id, flow in update_flows.items():
            self.record_flow(lane_id, flow)

    def flow_msg_decorate(self):
        lane_info = []
        for lane_id, flow in self.flows.items():
            record = {
                'laneId': lane_id,
                'flow': round(flow),
                'queueLength': 0,
                'queueNum': 0
            }
            lane_info.append(record)
        return lane_info


# @dataclass
# class PhaseDemand:
#     phase_id: int
#     movement_demands: List[MovementDemand]
#
#     def weight_saturation_rate(self, green_spilt: float):
#         priority_stack = []
#         saturation_stack = []
#         for demand in self.movement_demands:
#             priority_stack.append(PRIORITY_FACTOR[demand.priority])
#             saturation_stack.append(demand.saturation_rate(green_spilt))
#
#         total_proportion = sum(priority_stack)
#         weighted_saturation = 0
#         for factor, saturation in zip(priority_stack, saturation_stack):
#             weighted_saturation += saturation * factor / total_proportion
#         return weighted_saturation



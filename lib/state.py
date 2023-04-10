# -*- coding: utf-8 -*-
# @Time        : 2023/4/6 20:21
# @File        : state.py
# @Description :
from typing import List, Dict, Optional

from dataclasses import dataclass
from lib.SPAT import Turn

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

    def saturation_rate(self, lane_num, green_spilt: float):
        return self.flow_hour_total / (self.capacity_hour_per_lane * lane_num * green_spilt)

    def update(self, flow: float, queue_length: float):
        self.flow_hour_total = flow
        self.avg_queue_length = queue_length


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



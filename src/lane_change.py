# -*- coding: utf-8 -*-
# @Time        : 2023/4/6 20:15
# @File        : lane_change.py
# @Description :
import time

from collections import defaultdict, namedtuple
from typing import Tuple, List, Dict, Union, Optional, Callable

from lib.SPAT import Turn, Direction, Movement
from lib.state import TurnDemand, PlanDuration, DayLanePlan, LaneFlowQueueStorage, QueueData
from lib.tool import logger
from src.connection import Connection
from utils.data_load import HistoryLaneFlow

ABSOLUTE_SATURATION_DIFF = 0.35  # 流向饱和度不均判别阈差值
RECOVER_SATURATION_DIFF = 0.5  # 恢复主要流向时对次要流向饱和度保护差值
MINOR_CLEAR_SATURATION_THRESHOLD = 0.45  # 该饱和度以下认为次要方向为通畅状态，可恢复为主流向


class VMS:
    def __init__(self, initial_state: Turn, major_state: Turn, minor_state: Turn,
                 entity_state_func: Callable[[Turn], List[dict]]):
        """

        Args:
            initial_state: 初始状态
            major_state: 主要保证流向
            minor_state: 次要保证流向
            entity_state_func: 将当前VMS优先保障的流向状态转化成用于上报平台的字典数据
        """
        self.current_turn = initial_state
        self.major_state = major_state
        self.minor_state = minor_state
        self.entity_state_func = entity_state_func

    @property
    def is_major(self):
        return self.current_turn == self.major_state

    @property
    def is_minor(self):
        return self.current_turn == self.minor_state

    def change_state(self):
        self.current_turn = self.minor_state if self.is_major else self.major_state

    def get_vms_entity_msg(self):
        return self.entity_state_func(self.current_turn)


class LaneAllocation:
    def __init__(self, basic_allocation: Dict[Turn, int], flexible_allocation: List[Dict[Turn, float]],
                 historical_tod_ensure_plan: Dict[Turn, List[PlanDuration]] = None):
        """

        Args:
            basic_allocation: 所有非可变车道的各转向分配车道数
            flexible_allocation: 可变车道灵活组合的转向车道数分配方案
            historical_tod_ensure_plan: 现行的各时段优先保障的流量(使用历史数据需赋值)
        """
        self.basic_allocation = basic_allocation
        self.variable_state = flexible_allocation
        self.historical_tod_ensure_plan = historical_tod_ensure_plan

    def ensure_turn_allocation(self, priority_turn: Turn, minor_turn: Optional[Turn]) -> Dict[Turn, float]:
        """
        寻找预选方案下最优的车道分配方案
        Args:
            priority_turn: 优先分配通行资源的转向
            minor_turn: 次要分配通行资源的转向,可为空

        Returns:

        """
        turn_count_allocation = defaultdict(list)
        for turn_addition in self.variable_state:
            tmp_allocation = {turn: self.basic_allocation[turn] + addition_lane_num for turn, addition_lane_num in
                              turn_addition.items()}
            turn_count = tmp_allocation[priority_turn]
            turn_count_allocation[turn_count].append(tmp_allocation)
        major_turn_lane_num, best_allocation_candidates = max(turn_count_allocation.items(), key=lambda x: x[0])
        if minor_turn is None:
            best_allocation = best_allocation_candidates[0]
        else:
            best_allocation = max(best_allocation_candidates, key=lambda x: x[minor_turn])
        return best_allocation

    def get_turn_sorted_lane_dynamic(self, current_hour: float) -> Optional[Dict[Turn, float]]:
        """
        由静态历史动态车道方案提取分配的车道数
        Args:
            current_hour:

        Returns:

        """
        if self.historical_tod_ensure_plan is None:
            return None

        for ensure_turn, plan_duration in self.historical_tod_ensure_plan.items():
            if any(duration.hour_start <= current_hour < duration.hour_end for duration in plan_duration):
                break
        else:
            raise ValueError(f'cannot find the location of current hour {current_hour} in the plan')

        return self.ensure_turn_allocation(ensure_turn, None)


class VarianceLane:
    def __init__(self, direction: Direction, vms_device: VMS, sat_threshold: Dict[Turn, float],
                 demands: List[TurnDemand], lane_allocation: LaneAllocation,
                 green_spilt: Dict[Turn, Union[float, Tuple[float]]]):
        self.direction = direction
        self.vms_device = vms_device
        self.demand = {demand.turn: demand for demand in demands}
        self.saturation_threshold = sat_threshold
        self.lane_allocation = lane_allocation
        self.green_split = green_spilt

    def update_demand(self, turn: Turn, flow_hour: float, queue_length: float):
        composition_num, decompose_turns, split_factor = turn.decompose()
        if composition_num > 1:
            for index, single_turn in enumerate(decompose_turns):
                split = split_factor[index] if split_factor is not None else 1 / composition_num
                self.demand[single_turn].update(flow_hour * split, queue_length)
        else:
            self.demand[decompose_turns[0]].update(flow_hour, queue_length)

    def vsm_adjust(self):
        MAJOR_EXTREME_THRESHOLD = 1.0
        vms = self.vms_device
        major_demand = self.demand[vms.major_state]
        minor_demand = self.demand[vms.minor_state]
        major_turn = major_demand.turn
        minor_turn = minor_demand.turn
        major_threshold = self.saturation_threshold[major_turn]
        minor_threshold = self.saturation_threshold[minor_turn]
        if vms.is_major:
            available_lane = self.lane_allocation.ensure_turn_allocation(major_turn, minor_turn)  # 当前车道分配方案
            # 检查是否次要转向饱和度超出阈值，或次要转向饱和度与主要转向饱和度差异过大
            green_split_candidate = self.green_split[minor_turn]
            if isinstance(green_split_candidate, tuple):
                minor_min_green_split = min(green_split_candidate)
                minor_max_green_split = max(green_split_candidate)
            else:
                minor_min_green_split = minor_max_green_split = green_split_candidate
            minor_current_saturation_rate = minor_demand.saturation_rate(minor_min_green_split,
                                                                         available_lane[minor_turn])
            major_current_saturation_rate = major_demand.saturation_rate(self.green_split[major_turn],
                                                                         available_lane[major_turn])
            print(self.direction, major_current_saturation_rate, minor_current_saturation_rate,
                  major_current_saturation_rate - minor_current_saturation_rate)
            if minor_current_saturation_rate > minor_threshold or \
                    minor_current_saturation_rate - major_current_saturation_rate > ABSOLUTE_SATURATION_DIFF:
                output_string = f'进口道{self.direction}转向{minor_turn}饱和度:{minor_current_saturation_rate},' \
                                f'饱和度阈值:{minor_threshold}, 车道功能变换  '

                adjust_available_lane = self.lane_allocation.ensure_turn_allocation(minor_turn, major_turn)
                major_adjust_sat_rate = major_demand.saturation_rate(self.green_split[major_turn],
                                                                     adjust_available_lane[major_turn])
                minor_adjust_sat_rate = minor_demand.saturation_rate(minor_max_green_split,
                                                                     adjust_available_lane[minor_turn])
                #  或主流向饱和度大于次流向一定水平, 且已经超过接受阈值, 则不变换
                if major_adjust_sat_rate + 0.2 > minor_adjust_sat_rate and major_adjust_sat_rate > major_threshold:
                    logger.info(output_string + f'车道方案改变后,主转向{major_turn}饱和度:{major_adjust_sat_rate}, '
                                                f'次转向{minor_turn}饱和度:{minor_adjust_sat_rate}'
                                                f'超过饱和度阈值{major_threshold}, 不改变车道功能分配方案')
                    return False
                print(output_string + str(major_adjust_sat_rate) + '  ' + str(minor_adjust_sat_rate))
                # do something here
                vms.change_state()
                return True
        else:
            available_lane = self.lane_allocation.ensure_turn_allocation(minor_turn, major_turn)
            green_split_candidate = self.green_split[minor_turn]
            if isinstance(green_split_candidate, tuple):
                minor_min_green_split = min(green_split_candidate)
                minor_max_green_split = max(green_split_candidate)
            else:
                minor_min_green_split = minor_max_green_split = green_split_candidate
            major_current_saturation_rate = major_demand.saturation_rate(self.green_split[major_turn],
                                                                         available_lane[major_turn])
            minor_current_saturation_rate = minor_demand.saturation_rate(minor_max_green_split,
                                                                         available_lane[minor_turn])
            print(self.direction, major_current_saturation_rate, minor_current_saturation_rate,
                  major_current_saturation_rate - minor_current_saturation_rate)

            adjust_available_lane = self.lane_allocation.ensure_turn_allocation(major_turn, minor_turn)
            minor_adjust_sat_rate = self.demand[minor_turn].saturation_rate(minor_min_green_split,
                                                                            adjust_available_lane[minor_turn])
            major_adjust_sat_rate = self.demand[major_turn].saturation_rate(self.green_split[major_turn],
                                                                            adjust_available_lane[major_turn])
            # 优先保证major流向, 判断条件符合以下之一: 1) 主流向饱和度高于阈值, 2) 主流向高于次要流向较多
            if major_current_saturation_rate > MAJOR_EXTREME_THRESHOLD or \
                    major_current_saturation_rate - minor_current_saturation_rate > ABSOLUTE_SATURATION_DIFF:
                output_string = f'进口道{self.direction.name}主要转向{major_turn}饱和度:{major_current_saturation_rate}, ' \
                                f'次要转向{minor_turn}饱和度:{minor_current_saturation_rate}, 车道功能变换  '

                if minor_adjust_sat_rate > major_adjust_sat_rate + RECOVER_SATURATION_DIFF:
                    print(output_string + f'车道方案改变后,次转向{minor_turn}饱和度:{minor_adjust_sat_rate}, '
                                                f'显著大于主转向{major_turn}饱和度:{major_adjust_sat_rate}, 不改变车道功能分配方案')
                    return False
                print(output_string)
                vms.change_state()
                return True

            # 低流量状态尝试恢复为主要流向, 切换后次要流向仍处于通畅状态
            if minor_adjust_sat_rate <= MINOR_CLEAR_SATURATION_THRESHOLD:
                print(f'车道方案改变后, 次转向{minor_turn}饱和度:{minor_adjust_sat_rate}, 仍处于通畅状态, 恢复为主流向状态, '
                      '车道功能变换')
                vms.change_state()
                return True

        # 未达到所设阈值, 不触发车道变换
        return False


def lane_volume_retrieve(lane_traffic_info: dict, stat_duration_sec: float):
    lane_id = lane_traffic_info['lane_no']
    volume_duration = lane_traffic_info['volume']
    volume_hour = volume_duration / stat_duration_sec * 3600
    return lane_id, volume_hour


def get_movement_sorted_lane(lane_movement_mapping: Dict[int, Movement]) -> Dict[Movement, List[int]]:
    movement_sorted_lanes = defaultdict(list)
    for lane_id, movement in lane_movement_mapping.items():
        movement_sorted_lanes[movement].append(lane_id)
    return movement_sorted_lanes


class IntersectionController:
    def __init__(self, variance_lanes: List[VarianceLane], lane_movement_mapping: Dict[int, Movement],
                 update_interval_sec: float, history_lane_movement_mapping: DayLanePlan):
        self.variance_lanes: Dict[Direction, VarianceLane] = {v_lane.direction: v_lane for v_lane in variance_lanes}
        self.lane_movement_mapping = lane_movement_mapping
        self.movement_sorted_lanes = get_movement_sorted_lane(lane_movement_mapping)
        self.traffic_data_cache = {lane_id: [] for lane_id in lane_movement_mapping.keys()}
        self.queue_data_cache = {lane_id: [] for lane_id in lane_movement_mapping.keys()}
        self.update_interval_sec = update_interval_sec
        self.last_update_time = None
        self.history_lane_plan = history_lane_movement_mapping

    def calculate_movement_avg_flow_stat(self, movement_sorted_lanes: Dict[Movement, List[int]]):
        """从缓存中读取交通流数据并更新需求"""
        for movement, lanes_id in movement_sorted_lanes.items():
            movement_total_avg_flow = 0
            for lane_id in lanes_id:
                stats = self.traffic_data_cache[lane_id]
                avg_flow = sum(stats) / len(stats) if len(stats) else 0
                movement_total_avg_flow += avg_flow

            yield movement, movement_total_avg_flow

    def update_all_movement_demand(self, movement_sorted_lanes: Dict[Movement, List[int]], **kwargs):
        for movement, movement_total_avg_flow in self.calculate_movement_avg_flow_stat(movement_sorted_lanes):
            self.variance_lanes[movement.direction].update_demand(movement.turn, movement_total_avg_flow, 0)

    def variance_lane_change_decide(self) -> bool:
        change_flag = False
        for direction, v_lane in self.variance_lanes.items():
            change_state = v_lane.vsm_adjust()
            if change_state:
                print(
                    f'进口道{direction}车道功能变换, 当前模式{"主要流向" if v_lane.vms_device.is_major else "次要流向"}')
                change_flag = True
        # 清除缓存的数据
        for cache in self.traffic_data_cache.values():
            cache.clear()
        return change_flag

    def update_from_traffic_flow(self, tf_data: dict):
        detect_start_time = tf_data['cycle_start_time']
        if self.last_update_time is None:
            self.last_update_time = detect_start_time
        detect_duration = tf_data['cycle_time']
        for lane_info in tf_data['lanes']:
            lane_id, volume_hour = lane_volume_retrieve(lane_info, detect_duration)
            if lane_id not in self.lane_movement_mapping:
                continue

            # movement = self.lane_movement_mapping[lane_id]
            # if movement.direction not in self.variance_lanes:
            #     continue

            self.traffic_data_cache[lane_id].append(volume_hour)

        if detect_start_time - self.last_update_time >= self.update_interval_sec:
            self.calculate_movement_avg_flow_stat(self.movement_sorted_lanes)
            self.variance_lane_change_decide()
            self.last_update_time = detect_start_time
            print(time.asctime(time.gmtime(detect_start_time)))

    def update_from_queue(self, queue_data: dict):
        for lane in queue_data['lanes']:
            lane_id = lane['lane_no']
            if lane_id not in self.lane_movement_mapping:
                continue

            queue_avg = lane['queue']
            queue_num = queue_avg['queue_num']
            queue_length = queue_avg['queue_length']
            self.queue_data_cache[lane_id].append(QueueData(queue_num, queue_length))


class StaticIntersectionController(IntersectionController):
    def __init__(self, variance_lanes: List[VarianceLane], lane_movement_mapping: Dict[int, Movement],
                 update_interval_sec: float, history_lane_movement_mapping: DayLanePlan):
        super().__init__(variance_lanes, lane_movement_mapping, update_interval_sec, history_lane_movement_mapping)
        
        # self.peak_lane_movement_mapping = peak_lane_movement_mapping
        # self.peak_movement_sorted_lanes = get_movement_sorted_lane(peak_lane_movement_mapping)
        # self.peak_hour_range = peak_hour_range

    def update_from_traffic_flow(self, tf_data: dict):
        # Do not use this method
        detect_start_time = tf_data['cycle_start_time']
        if self.last_update_time is None:
            self.last_update_time = detect_start_time

        detect_duration = tf_data['cycle_time']
        for lane_info in tf_data['lanes']:
            lane_id, volume_hour = lane_volume_retrieve(lane_info, detect_duration)
            if lane_id not in self.lane_movement_mapping:
                continue

            self.traffic_data_cache[lane_id].append(volume_hour)

        if detect_start_time - self.last_update_time >= self.update_interval_sec:
            current_time = time.localtime(detect_start_time)
            if self.peak_hour_range[0] <= current_time.tm_hour < self.peak_hour_range[1]:
                movement_sorted_lane = self.peak_movement_sorted_lanes
                # if self.variance_lanes[Direction.EAST].vms_device.is_major:
                #     self.variance_lanes[Direction.EAST].vms_device.change_state()
            else:
                movement_sorted_lane = self.movement_sorted_lanes
                # if self.variance_lanes[Direction.EAST].vms_device.is_minor:
                #     self.variance_lanes[Direction.EAST].vms_device.change_state()

            self.update_all_movement_demand(movement_sorted_lane)
            self.variance_lane_change_decide()
            self.last_update_time = detect_start_time
            print(time.asctime(current_time), end='\n\n')
    
    def update_from_complete_data(self, flow_data: Dict[int, float], current_hour: float):
        plan_duration = self.history_lane_plan.search_plan(current_hour)
        movement_lane_mapping = get_movement_sorted_lane(plan_duration.movement_allocation)
        for movement, lanes_id in movement_lane_mapping.items():
            movement_total_flow = 0
            for lane_id in lanes_id:
                movement_total_flow += flow_data[lane_id]
            self.variance_lanes[movement.direction].update_demand(movement.turn, movement_total_flow, 0)
        
        self.variance_lane_change_decide()
        

class DynamicIntersectionController(IntersectionController):
    def __init__(self, variance_lanes: List[VarianceLane], lane_movement_mapping: Dict[int, Movement],
                 update_interval_sec: float, history_lane_flow: Dict[int, HistoryLaneFlow],
                 history_lane_movement_mapping: DayLanePlan, plan_applied: bool = False, connection: Connection = None):
        """

        Args:
            variance_lanes:
            lane_movement_mapping:
            update_interval_sec:
            history_lane_flow:
            history_lane_movement_mapping:
            plan_applied:
            connection: MQTT连接
        """
        super().__init__(variance_lanes, lane_movement_mapping, update_interval_sec, history_lane_movement_mapping)
        self.history_lane_flow = history_lane_flow
        self.plan_applied = plan_applied  # TODO: 如果执行方案可直接影响车道功能, 将不使用预设车道方案而使用内部存储方案
        self.lane_flow_storage = LaneFlowQueueStorage(lane_movement_mapping.keys())
        self.connection = connection

    def calculate_movement_avg_flow_stat_predicted(self, movement_sorted_lanes: Dict[Movement, List[int]], **kwargs):
        for movement, lanes_id in movement_sorted_lanes.items():
            movement_total_avg_flow = 0
            for lane_id in lanes_id:
                stats = self.traffic_data_cache[lane_id]
                avg_flow = sum(stats) / len(stats) if len(stats) else 0

                last_step_flow = self.lane_flow_storage.get_lane_flow_last_step(lane_id)
                if last_step_flow < 0:
                    last_step_flow = None
                predict_lane_flow = self.history_lane_flow[lane_id].predict_one_step(kwargs['current_hour'], avg_flow,
                                                                                     kwargs['date_type'],
                                                                                     last_step_flow)

                movement_total_avg_flow += predict_lane_flow
                self.lane_flow_storage.record_flow(lane_id, avg_flow)

            yield movement, movement_total_avg_flow

    def update_all_movement_demand(self, movement_sorted_lanes: Dict[Movement, List[int]], **kwargs):
        for movement, movement_total_avg_flow in self.calculate_movement_avg_flow_stat_predicted(movement_sorted_lanes,
                                                                                                 **kwargs):
            self.variance_lanes[movement.direction].update_demand(movement.turn, movement_total_avg_flow, 0)

    def update_all_lane_queue(self):
        for lane_id, queue_cache in self.queue_data_cache.items():
            self.lane_flow_storage.record_queue(lane_id, queue_cache)
            queue_cache.clear()

    def update_from_traffic_flow(self, tf_data: dict, publish: bool = False):
        # tf_data = tf_data['statistics'][0]
        detect_start_time = tf_data['cycle_start_time']
        if self.last_update_time is None:
            self.last_update_time = detect_start_time

        detect_duration = tf_data['cycle_time']
        for lane_info in tf_data['lanes']:
            lane_id, volume_hour = lane_volume_retrieve(lane_info, detect_duration)
            if lane_id not in self.lane_movement_mapping:
                continue

            self.traffic_data_cache[lane_id].append(volume_hour)

        if detect_start_time - self.last_update_time >= self.update_interval_sec:
            time.sleep(0.2)
            current_time = time.localtime(detect_start_time)
            current_hour = current_time.tm_hour + current_time.tm_min / 60
            plan_duration = self.history_lane_plan.search_plan(current_hour)
            self.update_all_movement_demand(get_movement_sorted_lane(plan_duration.movement_allocation),
                                            current_hour=current_hour, date_type=self.get_date_type(current_time))

            # queue数据没有时间戳信息, 需要在此处进行更新
            self.update_all_lane_queue()

            change_flag = self.variance_lane_change_decide()
            self.last_update_time = detect_start_time
            print(time.asctime(current_time), end='\n\n')

            if publish and self.connection is not None:
                self.connection.publish_tf(self.lane_flow_record())
                if change_flag:
                    self.connection.publish_vms(self.vms_state_record())

    def lane_flow_record(self) -> dict:
        """获得车道级流量数据, 需要调用calculate_movement_avg_flow_stat_predicted后才可获得最新数据"""
        lane_data = self.lane_flow_storage.flow_msg_decorate()
        msg = {
            'timestamp': int(time.time()),
            'duration': self.update_interval_sec,
            'laneData': lane_data
        }
        return msg

    def vms_state_record(self) -> dict:
        """生成VMS状态信息"""
        lane_allocation = []
        for direction, v_lane in self.variance_lanes.items():
            vms = v_lane.vms_device
            lane_allocation.extend(vms.get_vms_entity_msg())
        msg = {
            'timestamp': int(time.time()),
            'duration': self.update_interval_sec,
            'laneAllocations': lane_allocation
        }
        return msg

    def get_date_type(self, current_time: time.struct_time):
        # TODO: festival
        date_type = 'weekends' if current_time.tm_wday >= 5 else 'weekdays'
        return date_type

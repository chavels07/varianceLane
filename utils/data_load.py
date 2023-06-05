# -*- coding: utf-8 -*-
# @Time        : 2023/5/30 22:47
# @File        : data_load.py
# @Description :

import csv
import math
import os
from datetime import datetime
from functools import partial
from typing import List, Dict, Any, Iterable, Optional


class HistoryLaneFlow:
    def __init__(self, lane_id: int, split_interval_hour: float, date_type: Iterable[str]):
        self.lane_id = lane_id
        self.split_interval = split_interval_hour
        assert 24 % split_interval_hour == 0, f'分割时段长度{split_interval_hour}h 不能使单日被整除'
        self.split_num = int(24 // split_interval_hour)
        self._tod_flow_cache: Dict[str, Dict[int, List[int]]] = {date: {i: [] for i in range(0, self.split_num)} for
                                                                 date in
                                                                 date_type}
        self.tod_flow: Optional[Dict[str, Dict[int, float]]] = None

    def append_flow_data(self, flow: int, minute_in_day: int, date_type: str):
        interval_index = round(minute_in_day / 60 / self.split_interval)
        self._tod_flow_cache[date_type][interval_index].append(flow)

    def calculate_avg_flow(self):
        self.tod_flow = {}
        for date_type, tod_flow in self._tod_flow_cache.items():
            self.tod_flow[date_type] = {}
            for split_index, flow_record in tod_flow.items():
                self.tod_flow[date_type][split_index] = sum(flow_record) / len(flow_record) if len(flow_record) else 0

        # self.tod_flow = {split_index: sum(flow_record) / len(flow_record) if len(flow_record) else 0 for date_type,
        #                  tod_flow in self._tod_flow_cache.items() for split_index, flow_record in tod_flow.items()}

    def _backward_window_flow(self, current_hour: float, date_type: str, backward_num: int = 0):
        """向后寻找n个时间窗的历史流量信息, n为0时代表预测当前时间的下一个窗口"""
        current_hour = (current_hour - backward_num * self.split_interval) % 24
        split_index = current_hour / self.split_interval
        current_index = int(split_index)
        next_index = (current_index + 1) % self.split_num
        current_window_fraction = (split_index - current_index) / self.split_interval
        next_window_fraction = ((next_index - split_index) % 24) / self.split_interval
        current_step_history_flow = self.tod_flow[date_type][current_index]
        next_step_history_flow = self.tod_flow[date_type][next_index]
        mixed_flow = current_step_history_flow * current_window_fraction + next_step_history_flow * next_window_fraction
        return mixed_flow

    def predict_one_step(self, current_hour: float, current_flow: float, date_type: str, last_step_flow: float = None,
                         restrict_diff: float = 200):
        """
        预测下一个时间步的流量情况，根据当前时间步流量实际变化量和历史变化量的匹配程度确定取下一时间步历史变化和当前步变化的加权
        Args:
            current_hour: 当前时间(h)
            current_flow: 当前检测流量
            date_type: 当前日期类型
            last_step_flow: 上一时间步的流量
            restrict_diff: 限制预测和历史下一步时间流量的最大变化值, 超出则进行一个插值修正

        Returns:
            下一时间步预测流量
        """
        _history_flow_func = partial(self._backward_window_flow, current_hour, date_type)
        history_next_flow = _history_flow_func(0)
        history_current_flow = _history_flow_func(1)
        if last_step_flow is not None:
            current_diff = current_flow - last_step_flow
            history_diff = history_current_flow - _history_flow_func(2)
            history_next_diff = history_next_flow - history_current_flow
            belief_factor = math.exp(- abs(current_diff - history_diff) / abs(history_diff))  # 限制在0-1区间内
            # 利用历史的变化, 和实际前一时间步的变化进行加权得到预测变化, 前一时间步变化差异越大, 实时变化所占权重越高
            predict_next_diff = history_next_diff * belief_factor + current_diff * (1 - belief_factor)
        else:
            predict_next_diff = history_next_flow - history_current_flow
        predict_flow = current_flow + predict_next_diff
        RESTRICT_WEIGHT = 0.7
        if predict_flow <= 0:
            predict_flow = history_next_flow * RESTRICT_WEIGHT
        if abs(predict_flow - history_next_flow) > restrict_diff:
            predict_flow = predict_flow * RESTRICT_WEIGHT + history_next_flow * (1 - RESTRICT_WEIGHT)
        return predict_flow


def load_mature_data(file_path: str):
    with open(file_path, 'r+', newline='') as csv_f:
        csv_reader = csv.DictReader(csv_f)
        date_minute_sorted_data = {}
        for row in csv_reader:
            start_time = datetime.fromtimestamp(int(row.pop('start')))
            end_time = datetime.fromtimestamp(int(row.pop('end')))
            date = start_time.day
            minute_in_day = start_time.hour * 60 + start_time.minute
            date_minute_sorted_data.setdefault(date, {})[minute_in_day] = row
        # print(date_minute_sorted_data.keys())
        return date_minute_sorted_data


def date_classify_date(mature_data_dir_path: str, date_class: Dict[Any, List[int]], split_interval_hour: float,
                       lane_ids: List[int]) -> Dict[int, HistoryLaneFlow]:
    date_type_assemble_avg_flow: Dict[int, HistoryLaneFlow] = {lane_id: HistoryLaneFlow(lane_id, split_interval_hour,
                                                                                        date_class.keys())
                                                               for lane_id in lane_ids}
    for data_name in os.listdir(mature_data_dir_path):
        date_minute_sorted_data = load_mature_data(os.path.join(mature_data_dir_path, data_name))
        for date, minute_data in date_minute_sorted_data.items():
            for d_type, dates in date_class.items():
                if date in dates:
                    this_date_type = d_type
                    break
            else:
                raise ValueError(f'no specific date type for date {date}')

            for minute_in_day, flow_data in minute_data.items():
                for lane_id, flow in flow_data.items():
                    lane_num_id = int(''.join(filter(lambda x: x.isnumeric(), lane_id)))
                    date_type_assemble_avg_flow[lane_num_id].append_flow_data(int(flow), minute_in_day, this_date_type)
    for lane_id, lane_flow in date_type_assemble_avg_flow.items():
        lane_flow.calculate_avg_flow()
        print(lane_id, lane_flow.tod_flow)

    return date_type_assemble_avg_flow


if __name__ == '__main__':
    # load_mature_data('../data/history/TrafficFlow_Logs2.log.csv')
    date_classify_date('../data/history', {'weekdays': [4, 6, 7, 10, 11, 12], 'weekends': [8, 9], 'festivals': [5]}, 1,
                       [16, 17, 18, 19, 30, 31, 32, 33])

    import json
    import time
    now = int(time.mktime(time.localtime()))
    example = {'timestamp': now, 'duration': 1800, 'laneData': [{'LaneId': 17, 'flow': 356, 'queueLength': 56, 'queueNum':10}, {'LaneId': 18, 'flow': 298, 'queueLength': 60, 'queueNum':10}]}
    vms_example = {'timestamp': now, 'duration': 1800, 'laneAllocations': [{'vmsId': 1, 'laneId': 18, 'direction': 2, 'movement': 4}, {'vmsId': 2, 'laneId': 19, 'direction': 2, 'movement': 3}]}
    print(json.dumps(example))
    print(json.dumps(vms_example))
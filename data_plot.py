# -*- coding: utf-8 -*-
# @Time        : 2023/4/11 21:58
# @File        : data_plot.py
# @Description :

import time
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple
from xml.etree import ElementTree as ET

from lib.SPAT import Movement, Turn, Direction
from src.lane_change import lane_volume_retrieve
from process import read_file


class CacheList(list):
    @property
    def list_end(self):
        return self[-1] if self else None

    @list_end.setter
    def list_end(self, val):
        self[-1] = val

    def store(self, val):
        if not len(self) or isinstance(self.list_end, (float, int)):
            self.append([])
        self.list_end.append(val)

    def last_cache_stat(self):
        if not self or not isinstance(self.list_end, list):
            raise ValueError('Cannot get stat info with no data in cache')

        self.list_end = sum(self.list_end) / len(self.list_end)


class DataRecord:
    def __init__(self, valid_lane_id: List[int], update_interval: float):
        self.cache: Dict[int, CacheList] = {lane_id: CacheList() for lane_id in valid_lane_id}
        self.last_update_timestamp = -1
        self.update_interval = update_interval
        self.finished = False

    def record_write_if_necessary(self, current_timestamp: float):
        if self.last_update_timestamp == -1:
            self.last_update_timestamp = current_timestamp
            return False
        if current_timestamp >= self.last_update_timestamp + self.update_interval:
            for lane_id, cache_data in self.cache.items():
                cache_data.last_cache_stat()
            self.last_update_timestamp = current_timestamp
            return True
        return False

    def list_end_handle(self):
        if self.finished:
            return None
        for lane_id, cache_data in self.cache.items():
            cache_data.last_cache_stat()
        self.finished = True

    def pop_data_as_dict(self) -> Dict[int, List[float]]:
        return {lane_id: flow_data for lane_id, flow_data in self.cache.items()}


def data_retrieve(tf_data: dict, valid_day: int, valid_lane_id: List[int], record: DataRecord):
    start_timestamp = tf_data['cycle_start_time']
    start_time = time.localtime(start_timestamp)
    if start_time.tm_mday != valid_day:
        if start_time.tm_mday > valid_day:
            record.list_end_handle()
            return False
        return True

    record.record_write_if_necessary(start_timestamp)

    for lane_info in tf_data['lanes']:
        lane_id, volume_hour = lane_volume_retrieve(lane_info, tf_data['cycle_time'])
        if lane_id not in valid_lane_id:
            continue
        record.cache[lane_id].store(volume_hour)
    return True


def flow_plot(flow_data: Dict[int, List[float]], time_axis_15min):
    ax: plt.Axes
    fig, ax = plt.subplots(1)

    for index, (lane_id, flow) in enumerate(flow_data.items()):
        ax.plot(time_axis_15min, flow, label=lane_id, color=plt.cm.Paired(index))

    ax.legend()
    # ax.set_title('111')
    ax.set_ylim(0, 500)
    ax.set_xticks(time_axis_15min, time_axis_15min)
    ax.set_xlabel('Time (hour)', fontdict={'family': 'Times New Roman', 'size': 20})
    ax.set_ylabel('Volume (pcu/h)', fontdict={'family': 'Times New Roman', 'size': 20})
    plt.show()


def flow_movement_accumulate(flow_lane_data: Dict[int, List[float]],
                             lane_movements: Dict[int, Movement]) -> Dict[Movement, List[float]]:
    movement_flow = {}
    for lane_id, flow_in_duration in flow_lane_data.items():
        movement = lane_movements[lane_id]
        if movement.turn is Turn.RIGHT_TURN:
            movement_flow[Movement(movement.direction, Turn.RIGHT)] = [flow / 2 for flow in flow_in_duration]
            movement_flow[Movement(movement.direction, Turn.TURN)] = [flow / 2 for flow in flow_in_duration]
            continue
        res = movement_flow.get(movement, [0] * len(flow_in_duration))
        movement_flow[movement] = [num1 + num2 for num1, num2 in zip(res, flow_in_duration)]
    return movement_flow


def _indent(elem, level=0):
    i = '\n' + level * '\t'
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + '\t'
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for _elem in elem:
            _indent(_elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def route_xml_write(movement_flow: Dict[Movement, List[float]], interval_sec: float,
                    movement_edge_mapping: Dict[Movement, Tuple[str, str]], special_movement: List[Movement]):
    routes = ET.Element('routes')
    flow_counter = 1
    attrib_collections = []
    for movement, flow_data in movement_flow.items():
        for index, flow in enumerate(flow_data):
            start_time = int(index * interval_sec)
            end_time = int((index + 1) * interval_sec)
            attrib_collections.append({'id': f'flow{flow_counter}',
                                        'from': movement_edge_mapping[movement][0],
                                        'to': movement_edge_mapping[movement][1],
                                        'begin': str(start_time),
                                        'end': str(end_time),
                                        'vehsPerHour': str(int(flow)),
                                        'type': 'Normal2' if movement in special_movement else 'Normal1',
                                        'departLane': 'best'})
            flow_counter += 1
    attrib_collections = sorted(attrib_collections, key=lambda x: x['begin'])
    for attr in attrib_collections:
        ET.SubElement(routes, 'flow', attrib=attr)

    _indent(routes)
    tree = ET.ElementTree(routes)
    tree.write('output/real_route1.rou.xml', encoding='utf-8', xml_declaration=True)


def main():
    tf_data_path = 'data/TrafficFlow_Logs3.log'
    VALID_LANE_IDS = [16, 17, 18, 19, 30, 31, 32, 33]
    FILTER_DAY = 10
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
    data_record = DataRecord(VALID_LANE_IDS, update_interval=60 * 60)
    for stat in read_file(tf_data_path):
        if not data_retrieve(stat[0], FILTER_DAY, VALID_LANE_IDS, data_record):
            break

    holiday_flow = data_record.pop_data_as_dict()
    movement_flow = flow_movement_accumulate(holiday_flow, LANE_MOVEMENT_MAPPING)
    print(movement_flow)

    MOVEMENT_EDGE_MAPPING = {
        Movement(Direction.EAST, Turn.STRAIGHT): ('-gneE1', 'gneE0'),
        Movement(Direction.EAST, Turn.RIGHT): ('-gneE1', 'gneE2'),
        Movement(Direction.EAST, Turn.TURN): ('-gneE1', 'gneE1'),
        Movement(Direction.WEST, Turn.STRAIGHT): ('-gneE0', 'gneE1'),
        Movement(Direction.WEST, Turn.LEFT): ('-gneE0', 'gneE2'),
    }
    special_movements = [Movement(Direction.EAST, Turn.TURN), Movement(Direction.WEST, Turn.LEFT)]
    route_xml_write(movement_flow, 360, MOVEMENT_EDGE_MAPPING, special_movements)
    # flow_plot(holiday_flow, list(range(24 * 1)))


if __name__ == '__main__':
    main()

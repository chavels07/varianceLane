# -*- coding: utf-8 -*-
# @Time        : 2023/5/30 13:18
# @File        : data_dump.py
# @Description :

import csv
import os
from datetime import datetime
from typing import Tuple, List, Dict, Optional

from src.lane_change import lane_volume_retrieve
from utils.process import read_file


class AccumulateCache:
    def __init__(self, lane_ids: List[int], accumulate_interval_sec: float):
        self._cache: Dict[int, List[float]] = {lane_id: [] for lane_id in lane_ids}
        self.last_update_time = None
        self.interval = accumulate_interval_sec

    def store_data(self, lane_id: int, volume_hour: float):
        storage = self._cache.get(lane_id)
        if storage is None:
            return
        storage.append(volume_hour)

    def pop_data_query(self, current_time: float) -> Tuple[Optional[Dict[str, float]], float]:
        if self.last_update_time is None:
            self.last_update_time = current_time

        if current_time >= self.last_update_time + self.interval:
            tmp_last_update_time = self.last_update_time
            self.last_update_time = current_time
            avg_stat = {'lane' + str(lane_id): round(sum(stat) / len(stat)) if len(stat) else 0 for lane_id, stat in
                        self._cache.items()}
            for stat in self._cache.values():
                stat.clear()
            return avg_stat, tmp_last_update_time

        return None, self.last_update_time


def data_process_and_storage(dir_path: str,
                             lane_ids: List[int],
                             date_start: Optional[datetime] = None,
                             date_end: Optional[datetime] = None,
                             accumulate_interval_hour: int = 1):
    for file_n in os.listdir(dir_path):
        if not file_n.endswith('log'):
            continue

        cache = AccumulateCache(lane_ids, accumulate_interval_hour * 3600)
        dumped_data = []
        full_f_name = os.path.join(dir_path, file_n)
        for tf_data in read_file(full_f_name):
            tf_data = tf_data[0]
            detect_start_time = tf_data['cycle_start_time']
            detect_start_local_time = datetime.fromtimestamp(detect_start_time)
            if date_start is not None and detect_start_local_time.day < date_start.day or \
                    date_end is not None and detect_start_local_time.day >= date_end.day:
                continue

            detect_duration = tf_data['cycle_time']
            for lane_info in tf_data['lanes']:
                lane_id, volume_hour = lane_volume_retrieve(lane_info, detect_duration)
                cache.store_data(lane_id, volume_hour)

            record_data, last_update_time = cache.pop_data_query(detect_start_time)
            if record_data is not None:
                record_data.update({'start': last_update_time, 'end': detect_start_time})
                dumped_data.append(record_data)

        field_names = ['start', 'end']
        field_names.extend(sorted(item for item in dumped_data[0].keys() if item.startswith('lane')))
        store_date_data(dumped_data, full_f_name, dir_path, field_names)


def store_date_data(data: List[dict],
                    f_name: str,
                    data_dir_path: str,
                    field_names: List[str],
                    saved_dir_name: str = 'history'):
    stable_output_dir_path = os.path.join(data_dir_path, saved_dir_name)
    if not os.path.exists(stable_output_dir_path):
        os.mkdir(stable_output_dir_path)
    head, tail = os.path.split(f_name)
    file_name = '.'.join((os.path.join(head, saved_dir_name, tail), 'csv'))
    with open(file_name, 'w+', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=field_names)
        writer.writeheader()
        for row_dict in data:
            writer.writerow(row_dict)


if __name__ == '__main__':
    proj_path = os.path.dirname(os.getcwd())
    path = os.path.join(proj_path, 'data')
    LANE_IDS = [16, 17, 18, 19, 30, 31, 32, 33]
    data_process_and_storage(path, LANE_IDS, accumulate_interval_hour=1)

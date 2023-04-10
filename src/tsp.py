import numpy as np
from functools import lru_cache
from warnings import warn
from typing import List, Tuple, Union, Optional

from lib.SPAT import Detector


def _inner_variance(lane_volume: np.ndarray):
    """
    组内方差
    """
    variance = np.var(lane_volume, axis=1) * lane_volume.shape[1]
    var_norm = np.linalg.norm(variance)
    return var_norm


class TSP:
    def __init__(self, lane_volume: np.ndarray):
        """
        时间序列分割算法
        :param lane_volume: 车道流量
        """
        self.lane_volume = lane_volume

    # 在C++中考虑引入缓存池来记录部分函数调用的结果，起到等价于lru_cache的效果，显著提高运算速度
    @lru_cache(maxsize=128)
    def time_series_partition(self, *, k_partition: int, subset_length: Optional[int] = None, start: int = 0) -> Union[np.float32, Tuple[np.float32, tuple]]:
        """
        :param k_partition: 分割区间数量
        :param subset_length: 数据子集长度，迭代之初可为None，其余时候应为非None
        :param start: 开始的下标，从0开始计数
        :return:
        """
        spilt_num = k_partition - 1  # 分割点数量
        min_var, best_spilt = -1, 0
        if subset_length is None:
            subset_length = self.lane_volume.shape[1]  # 也是判断函数初始
        if spilt_num == 0:
            return _inner_variance(self.lane_volume[:, :subset_length]), ()  # 不划分时直接计算方差
        elif spilt_num == 1:
            assert subset_length > 1 and start == 0
            for i in range(1, subset_length):
                this_var = _inner_variance(self.lane_volume[:, :i]) + _inner_variance(self.lane_volume[:, i:subset_length])  # 存在至少一个分割点时start必为0
                if min_var < 0 or this_var < min_var:
                    min_var, best_spilt = this_var, (start+i-1,)  # 更新最优分割点
            return min_var, best_spilt  # best_spilt仍然表示分割点的下标(从0开始)
        else:
            min_var, last_best_spilt, best_spilt = -1, 0, ()
            # column_num = lane_volume.shape[1]
            # 表示第k-1个分割点的可行区间，额外-1因为下标index从0开始
            for j in range(spilt_num, subset_length):
                last_var, last2_best_spilt = self.time_series_partition(k_partition=k_partition-1, subset_length=j)
                this_var = last_var + _inner_variance(self.lane_volume[:, j: subset_length])
                if min_var < 0 or this_var < min_var:
                    min_var, last_best_spilt, best_spilt = this_var, j-1, last2_best_spilt + (j-1,)  # 更新最优分割点
            return min_var, best_spilt


class QuarterVolumeMat:
    def __init__(self, lanes: List[str]):
        self.local_time = -1
        self.lanes = lanes  # 涉及的车道id
        self.lane_num = len(lanes)
        self.lane_volume = None  # 车道流量数据
        self.__volume_cache = None  # np.array([[] for _ in range(self.lane_num)], dtype=np.float32)  # 累积流量存储
        self.lane_queue = None #车道排队长度数据
        self.__queue_cache = None #累积排队长度存储
        self.__last_mat_update = -1

        
    def append_queue(self, timestamp: int, detector_data: List[Detector]):
        assert timestamp > self.local_time
        if self.__last_mat_update < 0:
            self.__last_mat_update = timestamp  # 累积排队长度开始计时点
        new_column = np.zeros([self.lane_num, 1], dtype=np.int32)
        period = 0
        lane_counter = set()
        for detector in detector_data:
            try:
                new_column[self.lanes.index(detector.lane)] = detector.queue_length
                lane_counter.add(detector.lane)
                if not period:
                    period = detector.detected_period
            except ValueError:
                warn(f'{detector.lane} is not in current volume matrix')
        # 判断是否有缺少的车道数据，有则用上次历史数据代替
        missing_lane = lane_counter.difference(self.lanes)
        if missing_lane:
            for m_lane in missing_lane:
                # 确保有历史数据
                if self.__queue_cache.size > 0:
                    insert_index = self.lanes.index(m_lane)
                    new_column[insert_index] = self.__queue_cache[insert_index, -1]
        if self.__queue_cache is None:
            self.__queue_cache = new_column
        else:
            self.__queue_cache = np.concatenate((self.__queue_cache, new_column), axis=1)
        time_counter = timestamp + period - self.__last_mat_update
        if time_counter >=60 * 15:
            quarter_queue = np.mean(self.__queue_cache, axis=1) / time_counter * 900 #?
            quarter_queue = quarter_queue.reshape(-1, 1)
            # print(self.lane_queue)
            if self.lane_queue is None:
                self.lane_queue = quarter_queue
            else:
                self.lane_queue = np.concatenate((self.lane_queue, quarter_queue), axis=1)
            self.__last_mat_update = -1
            self.__queue_cache = None
        self.local_time = timestamp


    def append_volume(self, timestamp: int, detector_data: List[Detector]):
        assert timestamp > self.local_time
        if self.__last_mat_update < 0:
            self.__last_mat_update = timestamp  # 累积流量开始计时点
        new_column = np.zeros([self.lane_num, 1], dtype=np.float32)
        period = 0
        lane_counter = set()
        for detector in detector_data:
            try:
                new_column[self.lanes.index(detector.lane)] = detector.volume
                lane_counter.add(detector.lane)
                if not period:
                    period = detector.detected_period
            except ValueError:
                warn(f'{detector.lane} is not in current volume matrix')
        # 判断是否有缺少的车道数据，有则用上次历史数据代替
        missing_lane = lane_counter.difference(self.lanes)
        if missing_lane:
            for m_lane in missing_lane:
                # 确保有历史数据
                if self.__volume_cache.size > 0:
                    insert_index = self.lanes.index(m_lane)
                    new_column[insert_index] = self.__volume_cache[insert_index, -1]  # 上一次的历史数据代替
        if self.__volume_cache is None:
            self.__volume_cache = new_column
        else:
            self.__volume_cache = np.concatenate((self.__volume_cache, new_column), axis=1)  # 合并添加到缓存中
        time_counter = timestamp + period - self.__last_mat_update
        if time_counter >= 60 * 15:
            quarter_vol = np.sum(self.__volume_cache, axis=1) / time_counter * 900  # 转换为pcu/quarter
            quarter_vol = quarter_vol.reshape(-1, 1)
            # print(self.lane_volume)
            if self.lane_volume is None:
                self.lane_volume = quarter_vol
            else:
                self.lane_volume = np.concatenate((self.lane_volume, quarter_vol), axis=1)
            self.__last_mat_update = -1  # 清空计时
            self.__volume_cache = None
        self.local_time = timestamp


def partition_acceleration(lane_volume: np.ndarray, max_partition=10):
    """
    考虑边际递减效应的时间序列分割点算法，应使用该方法
    :param lane_volume: 车道流量数据
    :param max_partition: 最大分割区间数
    :return:
    """
    k = 2
    solver = TSP(lane_volume)
    this_var, this_spilt = solver.time_series_partition(k_partition=k)
    last_var, last_spilt = solver.time_series_partition(k_partition=1)
    last_acceleration = None
    while True:
        if k == max_partition + 1:
            return k - 1, last_spilt
        next_var, next_spilt = solver.time_series_partition(k_partition=k+1)
        acceleration = next_var - 2 * this_var + last_var  # second difference
        if last_acceleration is not None:
            if acceleration < last_acceleration:
                return k - 1, last_spilt
        else:
            last_acceleration = acceleration
        last_var, last_spilt = this_var, this_spilt  # 不需要重复计算
        this_var, this_spilt = next_var, next_spilt
        k += 1


if __name__ == '__main__':
    volume = np.array([[1, 1, 1, 600, 700, 800, 1400, 1700, 2, 2, 2, 2000, 2],
                       [1, 1, 1, 600, 700, 800, 1400, 1700, 2, 2, 2, 2000, 2],
                       [1, 1, 1, 600, 700, 800, 1400, 1700, 2, 2, 2, 2000, 2]])
    sol = TSP(volume)
    var, b_spilt = sol.time_series_partition(k_partition=4)
    print(var, b_spilt)

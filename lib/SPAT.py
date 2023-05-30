from collections import Counter, defaultdict
from enum import Enum
from dataclasses import dataclass, field, astuple, InitVar
from typing import List, Set, Tuple, Dict, Sequence, Optional, TypeVar, NewType, DefaultDict

PhaseId = TypeVar('PhaseId', int, str)
JunctionId = TypeVar('JunctionId', int, str)
EdgeId = NewType('EdgeId', str)  # 沿用SUMO中道路名称，实际是Link，Link此处表示交叉口内部的连接道路
LaneId = NewType('LaneId', str)


MANEUVERS_MAPPING = ['s', 'l', 'r']  # 只设置三个Maneuver


class LightState(Enum):
    UNAVAILABLE = 0
    RED = 3
    GREEN = 6
    YELLOW = 7

    @classmethod
    def from_str(cls, str_val: str):
        str_mapping = {
            'permissiveMovementAllowed': 6,
            'stopAndRemain': 3,
            'intersectionClearance': 7
        }
        int_val = str_mapping.get(str_val)
        if int_val is None:
            raise ValueError('invalid light state string')
        return cls(int_val)


@dataclass
class TimeChangeDetails:
    """
    只使用TimeCountingDown
    """
    start_time: int
    end_time: int  # likelyEndTime
    next_start_time: Optional[int] = None  # 可能用不到
    next_duration: Optional[int] = None


@dataclass
class PhaseState:
    light: LightState = LightState.UNAVAILABLE
    timing: Optional[TimeChangeDetails] = None


@dataclass
class Phase:
    id: PhaseId  # 该id与link的movement中id相对应
    phase_state: PhaseState  # 通常情况下不考虑双环八相位的offset，一个相位只有一个phase state


"""
以下为自定义的数据结构
"""


class Turn(Enum):
    UNKNOWN = 0
    LEFT = ord('l')
    LEFT_STRAIGHT = ord('l') + ord('s')
    STRAIGHT = ord('s')
    RIGHT_STRAIGHT = ord('r') + ord('s')
    RIGHT = ord('r')
    TURN = ord('t')
    RIGHT_TURN = ord('t') + ord('r')

    @property
    def basic_movement(self):
        if self is self.LEFT_STRAIGHT:
            return Turn.LEFT
        if self is self.RIGHT_STRAIGHT:
            return Turn.RIGHT
        else:
            return self

    @property
    def possible_conflict_movement(self):
        if self.basic_movement is self.LEFT:
            return self.STRAIGHT
        elif self.basic_movement is self.STRAIGHT:
            return self.LEFT
        else:
            return None

    def decompose(self) -> Tuple[int, List['Turn'], Optional[List[float]]]:
        """
        将多转向放行车道进行拆解
        Returns: 拆解车道数量, 车道组合, 车辆分配比例(需要由实测转向比例确定, None则均分)

        """
        if self is self.RIGHT_TURN:
            return 2, [self.RIGHT, self.TURN], [1, 1]
        elif self is self.RIGHT_STRAIGHT:
            return 2, [self.RIGHT, self.STRAIGHT], None
        elif self is self.LEFT_STRAIGHT:
            return 2, [self.LEFT, self.STRAIGHT], None  # 对于直左共用车道来说, 左转流量取车道所有流量
        return 1, [self], None


# 暂时不需要direction
class Direction(Enum):
    WEST = 1
    SOUTH = 2
    EAST = 3
    NORTH = 4

    @property
    def opposite_direction(self):
        return Direction((self.value + 1) % 4 + 1)


@dataclass(frozen=True)
class Movement:
    direction: Direction
    turn: Turn


@dataclass
class PhasePlan:
    green: int
    yellow: int = 3
    all_red: int = 0

    @property
    def total(self):
        return self.green + self.yellow + self.all_red

    def green_spilt(self, cycle_length: int):
        return self.green / cycle_length

# @dataclass
# class JunctionLink:
#     """
#     参考SUMO中交叉口内部的link定义方式
#     """
#     link_index: int  # 交叉口内部connection的index，注意：在SUMO仿真平台使用中则对应内部自定义的movement_id
#     edge_from: EdgeId  # 到达的edge
#     edge_to: EdgeId  # 离开的edge
#     lane_from: LaneId  # 到达的lane
#     _mov: InitVar[str]  # Mystr(qualifier=['s', 'l', 'r', 'L', 'R'])
#     width: float
#     movement: Movement = field(init=False)  # 转向
#
#     def __post_init__(self, _mov):
#         for char in _mov:
#             if char not in ('s', 'l', 'r', 'L', 'R'):
#                 raise ValueError(f'{_mov} is invalid for direction')
#
#         if len(_mov) > 1:
#             _mov = sum(map(lambda x: ord(x), _mov))
#         else:
#             _mov = ord(_mov)
#         self.movement = Movement(_mov)


# @dataclass
# class JunctionPhaseLink(JunctionLink):
#     phase_id: PhaseId
#
#
# @dataclass
# class Arm:
#     """
#     一个进口道对应一个Arm，包含多个JunctionLink
#     """
#     links: List[JunctionPhaseLink]
#
#
# @dataclass
# class Detector:
#     timestamp: float  # 时间戳
#     detected_period: float  # 检测器上报的周期
#     lane: LaneId
#     volume: int = 0
#     queue_length: int = 0
#
#     def as_tuple(self):
#         return astuple(self)
#
#
# @dataclass
# class TrafficFlow:
#     junction_id: JunctionId
#     interval: int
#     stats: List[Detector]
#
#     @property
#     def lane_sorted_stats(self):
#         """
#         lane作为键值的交通流状态信息字典
#         """
#         return {item.lane: item for item in self.stats}
#



# @dataclass
# class PhaseExtension:
#     """
#     包含link in junction的拓展信息，仅在本项目中使用
#     """
#     phase_id: PhaseId
#     plan: Optional[PhasePlan] = None
#     links: List[JunctionLink] = field(default_factory=list)
#     __movement_link_count: DefaultDict[Tuple[EdgeId, Movement], int] = field(init=False)
#     __edges: Set[EdgeId] = field(init=False)
#
#     def __post_init__(self):
#         link_movement_sorted = [(link.edge_from, link.movement) for link in self.links]
#         self.__movement_link_count = defaultdict(int)
#         for key, value in Counter(link_movement_sorted).items():
#             self.__movement_link_count[key] += value
#         self.__edges = {link.edge_from for link in self.links}
#
#     def append_link(self, link: JunctionLink):
#         self.links.append(link)
#         self.__movement_link_count[(link.edge_from, link.movement)] += 1
#         self.__edges.add(link.edge_from)
#
#     def append_links(self, links: List[JunctionLink]):
#         self.links.extend(links)
#         for link in links:
#             self.__movement_link_count[(link.edge_from, link.movement)] += 1
#             self.__edges.add(link.edge_from)
#
#     # @property
#     # def attached_links(self) -> Set[int]:
#     #     """
#     #     返回该相位所连接的link index
#     #     :return:
#     #     """
#     #     return {link.link_index for link in self.links}
#
#     @property
#     def attached_lanes(self) -> Set[LaneId]:
#         """
#         返回该相位所连接的lane string
#         :return:
#         """
#         return {link.lane_from for link in self.links}
#
#     #
#     # @property
#     # def attached_movement(self) -> Dict[Tuple[str, Movement], int]:
#     #     return self.__movement_link_count
#
#     @property
#     def conflict(self) -> bool:
#         """
#         判断是否存在直左冲突
#         :return:
#         """
#         conflict_movement = None
#         for link in self.links:
#             if link.movement.basic_movement is Movement.RIGHT:
#                 continue
#             if conflict_movement is None:
#                 assert link.movement.basic_movement is not Movement.RIGHT
#                 conflict_movement = (link.edge_from, link.movement)
#             elif link.movement is conflict_movement[1].possible_conflict_movement and link.edge_from != \
#                     conflict_movement[0]:
#                 return True
#         return False
#
#     def opposite_edge(self, this_edge: EdgeId, movement: Movement) -> EdgeId:
#         """
#         获取对向的进口道id，一个相位最多会对应两个进口道通行
#         Args:
#             this_edge:
#             movement:
#         """
#         assert len(self.__edges) > 1
#         conflict_movement = movement.possible_conflict_movement
#         for edge in self.__edges:
#             if edge != this_edge and (edge, conflict_movement) in self.__movement_link_count:
#                 return edge
#
#     def lane_num(self, edge: EdgeId, movement: Movement) -> int:
#         return self.__movement_link_count.get((edge, movement), 0)
#
#
# @dataclass
# class SignalExecution:
#     junction_id: JunctionId
#     phase_program: Dict[PhaseId, PhaseExtension]
#
#
# @dataclass
# class TrafficLight:
#     intersection_id: JunctionId
#     phases: List[Phase] = field(default_factory=list)

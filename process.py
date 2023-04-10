# -*- coding: utf-8 -*-
# @Time        : 2023/4/6 19:55
# @File        : process.py
# @Description :
import re
import json

pattern = re.compile('\[[\s\S]+\]\s([\s\S]+)')


def read_file(f_path):
    with open(f_path, 'r') as f:
        for line in f.readlines():
            match_res = pattern.match(line)
            res_json_val = match_res.group(1)
            res_val = json.loads(res_json_val)
            stat_res = res_val['statistics']
            yield stat_res


if __name__ == '__main__':
    tf_data_path = 'data/TrafficFlow_Logs2.log'
    read_file(tf_data_path)
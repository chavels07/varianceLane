# -*- coding: utf-8 -*-
# @Time        : 2023/6/3 17:20
# @File        : config.py
# @Description :
import json


class Config:
    mqtt_ip = '127.0.0.1'
    mqtt_port = 1883
    tf_topic = ''
    queue_topic = ''
    tf_up_topic = ''
    vms_up_topic = ''


def load_json(fp):
    with open(fp, 'r', encoding='utf-8') as f:
        setting = json.load(f)

    Config.mqtt_ip = setting['mqtt_ip']
    Config.mqtt_port = setting['mqtt_port']
    Config.tf_topic = setting['tf_topic']
    Config.queue_topic = setting['queue_topic']
    Config.tf_up_topic = setting['tf_up_topic']
    Config.vms_up_topic = setting['vms_up_topic']
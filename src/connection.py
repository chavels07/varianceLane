# -*- coding: utf-8 -*-
# @Time        : 2023/6/3 17:10
# @File        : connection.py
# @Description :

import json
import paho.mqtt.client as mqtt
from functools import partial
from typing import Callable

from utils.config import Config


def topic_decorate(*args):
    return [(topic, 0) for topic in args]


def on_connect(client, user_data, flags, rc):
    if rc == 0:
        print('Connect to MQTT Broker')
    else:
        raise ConnectionError(f'Fail to connect MQTT Broker, error code: {rc}')


def on_message(client, user_data, msg: mqtt.MQTTMessage, tf_handle: Callable, queue_handle: Callable):
    """
    接收到订阅主题消息的回调函数，算法的入口
    """

    if msg.topic == Config.tf_topic:
        tf_handle(json.loads(msg.payload))
    elif msg.topic == Config.queue_topic:
        queue_handle(json.loads(msg.payload))
    else:
        raise NotImplementedError(f'invalid topic {msg.topic}, msg {msg.payload}')


class Connection:
    def __init__(self):
        self.client = mqtt.Client()

    def connect(self, tf_handle=Callable, queue_handle=Callable):
        client = self.client
        client.on_connect = on_connect
        client.on_message = partial(on_message, tf_handle=tf_handle, queue_handle=queue_handle)
        client.connect(Config.mqtt_ip, Config.mqtt_port)
        client.subscribe(topic_decorate(Config.tf_topic, Config.queue_topic))

    def publish_tf(self, msg: dict):
        self.client.publish(Config.tf_up_topic, json.dumps(msg))
        print('publish trafficFlow successfully')

    def publish_vms(self, msg: dict):
        self.client.publish(Config.vms_up_topic, json.dumps(msg))
        print('publish vms successfully')
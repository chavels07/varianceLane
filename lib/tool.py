# -*- coding: utf-8 -*-
# @Time        : 2023/4/7 14:13
# @File        : tool.py
# @Description :
import logging

logging.basicConfig(format='%(asctime)s.%(msecs)03d [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='## %Y-%m-%d %H:%M:%S')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

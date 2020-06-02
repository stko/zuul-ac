#!/usr/bin/env python
# -*- coding: utf-8 -*-

# little hack to read QR code from local webcam
# setup:
#		sudo apt-get install zbar-tools
# 		sudo -H pip3 install paho-mqtt
# usage:
#	zbarcam | python3 qr_to_mqtt.py

import sys
import json

import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
	print("Connected with result code " + str(rc))

client = mqtt.Client()
client.on_connect = on_connect

client.connect("10.48.164.82", 1883, 60)

client.loop_start()

for line in sys.stdin:
	elements=line.strip().split(':')
	if elements[0]=="QR-Code":
		qrcode=":".join(elements[1:])
		json_msg={'qrcode':qrcode,'doorid':'ATDT5912,#61'}
		print(line, json.dumps(json_msg))
		client.publish("door/qrcode", json.dumps(json_msg))


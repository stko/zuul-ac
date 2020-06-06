#!/usr/bin/env python
# -*- coding: utf-8 -*-

# little hack to write MQTT to serial
# setup:
# 		sudo -H pip3 install paho-mqtt
# usage:
#	 python3 MQTT_to_serial.py

import sys
import paho.mqtt.client as mqtt
import serial
import time

def on_connect(client, userdata, flags, rc):
	print("Connected with result code " + str(rc))

def on_message(client, userdata, message):
    print("message received  ",str(message.payload.decode("utf-8")), "topic",message.topic,"retained ",message.retain)
    send_serial(message.payload + b'\r\n')

def send_serial(cmd):
    global ser
    ser.write(cmd)     # write the cmd
    line = ser.readline()   # read a '\n' terminated line
    while line:
        print(line.decode().replace('\r',''), end='')
        line = ser.readline()   # read a '\n' terminated line

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)
client.subscribe('serial/dial')

client.loop_start()

ser= serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
print(ser.name)         # check which port was really used
send_serial(b'AT S7=45 L1 V1 X4 E1\r\n')     # write a string

while True:
    time.sleep(1)    

ser.close()             # close portfor line in sys.stdin:

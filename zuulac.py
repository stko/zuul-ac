#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import webserver
import accessmanager

server=webserver.ws_create()
server.register("ac_",None,accessmanager.msg,accessmanager.dummy,accessmanager.dummy)
webserver.ws_thread(server)
print("return from Thread")
while(True):
	time.sleep(1)


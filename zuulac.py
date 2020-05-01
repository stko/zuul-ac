#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import webserver
import accessmanager
import storage
from messenger import Messenger
import zuullogger


class ModRef:
	def __init__(self):
		self.server = None
		self.accessmanager = None
		self.messenger = None
		self.store = None


def _(s): return s


messenger = None


def restart():
	global modref

	print('try to restart')
	if modref.messenger:
		modref.messenger.shutdown()
	messenger_token = modref.store.read_config_value("messenger_token")
	messenger_type = modref.store.read_config_value("messenger_type")
	print(messenger_token, messenger_type)
	if messenger_token and messenger_type:
		modref.messenger = Messenger(messenger_type, messenger_token, modref.accessmanager)
	else:
		logger.error(
			_("Config incomplete: No messenger_token or messenger_type"))
	print('restarted')


modref = ModRef()
logger = zuullogger.getLogger(__name__)
modref.store = storage.Storage(modref)
modref.server = webserver.ws_create(modref)

modref.accessmanager = accessmanager.AccessManager(
	modref, restart)
modref.server.register("ac_", None, modref.accessmanager.msg,
					   modref.accessmanager.dummy, modref.accessmanager.dummy)
modref.server.register("st_", None, modref.store.msg,
					   modref.store.dummy, modref.store.dummy)


restart()
webserver.ws_thread(modref.server)

while(True):
	time.sleep(1)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import webserver
import accessmanager
import storage
from messenger import Messenger
import zuullogger


# https://inventwithpython.com/blog/2014/12/20/translate-your-python-3-program-with-the-gettext-module/
'''
import gettext
localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'locale')
translate = gettext.translation('guess', localedir, fallback=True)
_ = translate.gettext
'''
_ = lambda s: s

messenger = None

def restart():
	global messenger
	global store

	print('try to restart')
	if messenger:
		messenger.shutdown()
	messenger_token=store.read_config_value("messenger_token")
	messenger_type=store.read_config_value("messenger_type")
	print(messenger_token,messenger_type )
	if messenger_token and messenger_type:
		messenger= Messenger(messenger_type,messenger_token,am)
	else:
		logger.error(_("Config incomplete: No messenger_token or messenger_type"))
	print('restarted')

logger = zuullogger.getLogger(__name__)
store = storage.Storage()
server=webserver.ws_create(store)

am= accessmanager.AccessManager(store,server,restart)
server.register("ac_",None,am.msg,am.dummy,am.dummy)
server.register("st_",None,store.msg,store.dummy,store.dummy)


restart()
webserver.ws_thread(server)

while(True):
	time.sleep(1)


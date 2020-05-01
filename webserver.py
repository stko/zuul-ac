#!/usr/bin/env python
# -*- coding: utf-8 -*-

from HTTPWebSocketsHandler import HTTPWebSocketsHandler
'''
credits:
combined http(s) and websocket server copied from
	https://github.com/PyOCL/httpwebsockethandler
	The MIT License (MIT)
	Copyright (c) 2015 Seven Watt

'''


import sys
import os
import threading
import ssl
import json
from base64 import b64encode
import argparse
import time

import threading

from pprint import pprint

from socketserver import ThreadingMixIn
from http.server import HTTPServer
from io import StringIO


class User:
	'''handles all user related data
	'''

	def __init__(self, name, ws):
		self.name = name
		self.ws = ws


modules = {}
ws_clients = []


class WSZuulHandler(HTTPWebSocketsHandler):

	def get_module(self, prefix):
		global modules
		try:
			return modules[prefix]
		except:
			return None

	def emit(self, type, config):
		message = {'type': type, 'config': config}
		self.send_message(json.dumps(message))

	def on_ws_message(self, message):
		if message is None:
			message = ''
		#self.log_message('websocket received "%s"', str(message))
		try:
			data = json.loads(message)
		except:
			self.log_message('%s', 'Invalid JSON')
			return
		#self.log_message('json msg: %s', message)

		if data['type'] == 'msg':
			self.log_message('msg %s', data['data'])

		else:
			unknown_msg = True
			global modules
			for id, module in modules.items():
				if data['type'].lower().startswith(id):
					module["msg"](data, self.user)
					unknown_msg = False
			if unknown_msg:
				self.log_message("Command not found:"+data['type'])

	def on_ws_connected(self):
		self.log_message('%s', 'websocket connected')
		self.user = User("", self)
		global ws_clients
		ws_clients.append(self.user)
		global modules
		for module in modules.values():
			module["onWebSocketOpen"](self.user)

	def on_ws_closed(self):
		self.log_message('%s', 'websocket closed')
		global ws_clients
		ws_clients.remove(self.user)
		global modules
		# for module in modules.values():
		for module_name, module in modules.items():
			module["onWebSocketClose"](self.user)

	def setup(self):
		super(HTTPWebSocketsHandler, self).setup()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	"""Handle requests in a separate thread."""

	def register(self, prefix, module, wsMsghandler, wsOnOpen, wsOnClose):
		global modules
		modules[prefix] = {'module': module, 'msg': wsMsghandler,
						   'onWebSocketOpen': wsOnOpen, 'onWebSocketClose': wsOnClose}

	def get_module(self, prefix):
		global modules
		try:
			return modules[prefix]
		except:
			return None

	def emit(self, topic, data):
		global ws_clients
		for user in ws_clients:
			user.ws.emit(topic, data)


def ws_create(modref):
	server_config = modref.store.read_config_value("server_config")
	if not server_config:
		server_config = {
			'host': 'any',
			'port': 8000,
			'secure': False,
			'credentials': ''
		}
	modref.store.write_config_value("server_config", server_config)

	parser = argparse.ArgumentParser()
	parser.add_argument("--host", default=server_config["host"],
						help="the IP interface to bound the server to")
	parser.add_argument("-p", "--port", default=server_config["port"],
						help="the server port")
	parser.add_argument("-s", "--secure", action="store_true", default=server_config["secure"],
						help="use secure https: and wss:")
	parser.add_argument("-c", "--credentials",  default=server_config["credentials"],
						help="user credentials")
	args = parser.parse_args()
	print(repr(args))
	server = ThreadedHTTPServer((args.host, args.port), WSZuulHandler)
	server.daemon_threads = True
	server.auth = b64encode(args.credentials.encode("ascii"))
	if args.secure:
		server.socket = ssl.wrap_socket(
			server.socket, certfile='./server.pem', keyfile='./key.pem', server_side=True)
		print('initialized secure https server at port %d' % (args.port))
	else:
		print('initialized http server at port %d' % (args.port))
	return server


def _ws_main(server):
	try:

		origin_dir = os.path.dirname(__file__)
		web_dir = os.path.join(os.path.dirname(__file__), 'public')
		os.chdir(web_dir)

		server.serve_forever()

		os.chdir(origin_dir)
	except KeyboardInterrupt:
		print('^C received, shutting down server')
		server.socket.close()


def ws_thread(server):

	# Create a Thread with a function without any arguments
	th = threading.Thread(target=_ws_main, args=(server,))
	# Start the thread
	th.setDaemon(True)
	th.start()


if __name__ == '__main__':
	ws_thread()

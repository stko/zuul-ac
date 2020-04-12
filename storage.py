#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

import zuullogger
import translate

_ = translate.gettext

logger = zuullogger.getLogger(__name__)
class Storage:
	def __init__(self):
		''' loads all data files'''
		self.config = {}
		self.users = {'users':{'1137173018':{}},'followers':{}}
		self.config_file_name=os.path.join(os.path.dirname(__file__), 'config.json')
		self.users_file_name=os.path.join(os.path.dirname(__file__), 'users.json')

		try:
			with open(self.config_file_name) as json_file:
				self.config = json.load(json_file)

		except:
			logger.warning(_("couldn't load config file {0}").format(config_file_name))

		try:
			with open(self.users_file_name) as json_file:
				self.users = json.load(json_file)

		except:
			logger.warning(_("couldn't load users file {0}").format(self.users_file_name))

	def read_config_value(self,key):
		''' read value from config, identified by key

		Args:
		key (:obj:`str`): lookup index
		'''

		if key in self.config:
			return self.config[key]
		return None


	def write_config_value(self, key, value):
		''' write value into config, identified by key.
		Saves also straigt to disk

		Args:
		key (:obj:`str`): lookup index
		value (:obj:`obj`): value to store
		'''

		self.config[key]=value
		try:
			with open(self.config_file_name, 'w') as outfile:
				json.dump(self.config, outfile, sort_keys=True, indent=4, separators=(',', ': '))
		except:
			logger.warning(_("couldn't write config file {0}").format(self.config_file_name))


	def write_users(self):
		''' Saves the users to disk
		'''

		try:
			with open(self.users_file_name, 'w') as outfile:
#				json.dump(self.users, outfile, sort_keys=True, indent=4, separators=(',', ': '))
				json.dump(self.users, outfile)
		except:
			logger.warning(_("couldn't write users file {0}").format(self.users_file_name))


	def get_users(self):
		''' returns the user data reference
		'''
		return self.users

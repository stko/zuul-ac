#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json

import zuullogger
import translate
import user

_ = translate.gettext

logger = zuullogger.getLogger(__name__)
class Storage:
	def __init__(self):
		''' loads all data files'''
		self.config = {}
		self.users = {'users':{},'timetables':{}} # just empty lists
		self.config_file_name=os.path.join(os.path.dirname(__file__), 'config.json')
		self.users_file_name=os.path.join(os.path.dirname(__file__), 'users.json')

		try:
			with open(self.config_file_name) as json_file:
				self.config = json.load(json_file)

		except:
			logger.warning("couldn't load config file {0}".format(config_file_name))

		try:
			with open(self.users_file_name) as json_file:
				self.users = json.load(json_file)

		except:
			logger.warning("couldn't load users file {0}".format(self.users_file_name))
		# copy admin acounts into the user list, if not already in
		for admin in self.get_admin_ids():
			if not admin in self.users['users']:
				self.users['users'][admin]={'user':user.User('Alice','Admin',admin,'en')}

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
			logger.warning("couldn't write config file {0}".format(self.config_file_name))

	def get_admin_ids(self):
		return self.read_config_value('admins')

	def write_users(self):
		''' Saves the users to disk
		'''

		try:
			with open(self.users_file_name, 'w') as outfile:
				print(json.dumps(self.users, sort_keys=True, indent=4, separators=(',', ': ')))
#				json.dump(self.users, outfile, sort_keys=True, indent=4, separators=(',', ': '))
				json.dump(self.users, outfile, sort_keys=True, indent=4, separators=(',', ': '))
		except Exception as ex:
			logger.warning("couldn't write users file {0} because {1}".format(self.users_file_name,ex))


	def get_users(self):
		''' returns the user data reference
		'''
		return self.users

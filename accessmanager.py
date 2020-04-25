#!/usr/bin/env python
# -*- coding: utf-8 -*-

import string
import secrets
import datetime
import queue
from threading import Thread, Lock
import defaults


class AccessManager:

	def __init__(self, store, smart_home_interface):
		self.store = store
		self.mutex = Lock()
		self.users = store.get_users()
		self.queue = queue.Queue()
		self.smart_home_interface = smart_home_interface
		self.garbage_collection(self.users['users'].copy())
		self.current_tokens = {}

	def msg(self, data, ws_user):
		if data['type'] == 'ac_otprequest':
			self.queue.put(data)
		if data['type'] == 'ac_tokenquery':
			ws_user.ws.emit(
				"tokenstate", {'valid': self.validate_token(data['config']['token'])})

	def dummy(self, user):
		pass

	def user_info(self, user):
		user_ref = self.user_info_by_id(user["user_id"])
		if user_ref:  # update the user with the latest just received data
			self.users['users'][user["user_id"]]['user'] = user
			return self.users['users'][user["user_id"]]['user']
		else:
			return user_ref

	def user_id(self, user):
		return user["user_id"]

	def user_is_active(self, current_user, active_user, time_table_id='1'):
		''' returns true if the user has no deletion time set'''
		# does the current user already have lend some keys?
		if not current_user["user_id"] in self.users['timetables']:
			return False
		if not active_user["user_id"] in self.users['timetables'][current_user["user_id"]][time_table_id]['users']:
			return False
		return self.users['timetables'][current_user["user_id"]][time_table_id]['users'][active_user["user_id"]] == None

	def user_can_lend(self, user):
		''' returns true if the user is allowed to lend his key further'''
		for depth in self.users['users'][user["user_id"]]['time_table']:
			if depth > 0:
				return True
		return False

	def add_user(self, current_user, new_user):
		'''Add a new user to the database'''
		old_user_table = self.users['users'].copy()
		self.users['users'][new_user["user_id"]] = {
			'user': new_user, 'time_table': None}
		# does the current user already have lend some keys?
		if not current_user["user_id"] in self.users['timetables']:
			# if not, create a storage for his lend keys
			'''
			each user has a set of timeplans, eacch with it's unique id
			each timeplan has a list[] of users assigned to that time plan
			The timeplan with the id '1' is the standard simple one without
			any limitations in times or duration

			in the actual version only this dummy time plan is used, just the
			structures for more complicated time plans are already made now
			for an eventual later enhancenment
			'''
			self.users['timetables'][current_user["user_id"]] = {
				'1': {'users': {}, 'deletion_timestamp': None}}
		# set the deletion date to None
		self.users['timetables'][current_user["user_id"]
								 ]['1']['users'][new_user["user_id"]] = None
		return self.garbage_collection(old_user_table)

	def get_follower_list(self, sponsor_user, time_table_id='1'):
		res = []
		if sponsor_user["user_id"] in self.users['timetables']:
			# for later enhancements. Actual there's only the standard id '1'
			for follower_id in self.users['timetables'][sponsor_user["user_id"]][time_table_id]['users']:
				# if a deletion date is not already set
				if not self.users['timetables'][sponsor_user["user_id"]][time_table_id]['users'][follower_id]:
					res.append({'text': self.users['users'][follower_id]['user']['first_name']+' '+self.users['users'][follower_id]['user']['last_name'],
								"user_id": follower_id})
		return res

	def get_sponsor_list(self, follower_user, time_table_id='1'):
		res = []
		follower_id = follower_user["user_id"]
		for sponsor_user_id in self.users['timetables']:
			for time_table in self.users['timetables'][sponsor_user_id].values():
				# important: users can also return keys out of inactive time tables, so we don't check if the table is active
				# no deletion date set
				if follower_id in time_table['users'] and not time_table['users'][follower_id]:
					res.append({'text': self.users['users'][sponsor_user_id]['user']['first_name']+' '+self.users['users'][sponsor_user_id]['user']['last_name'],
								"user_id": sponsor_user_id})
		return res

	def get_unix_timestamp(self):
		return datetime.datetime.utcnow().timestamp()

	def time_table_is_active(self, time_table):
		''' returns the active state of the time table'''

		if not time_table:
			return False
		# as time tables are not implemented yet, we check only the deletion data

		if time_table["deletion_timestamp"]:
			# older as  defaults.DELETE_AFTER_DAYS days
			if time_table["deletion_timestamp"] < self.get_unix_timestamp - 60 * 60 * 24 * defaults.DELETE_AFTER_DAYS:
				return False
		return True

	def create_full_time_table(self):
		''' helper routine to create a full packet time table for the admins'''
		res = []
		ttl = self.store.read_config_value('timetolive', 5)
		for i in range(defaults.TIME_TABLE_SIZE):  # for each entry slot
			res.append(ttl)
		return res

	def calculate_follower_time_table(self, sponsor_table, ruleset, follower_table):
		if not follower_table:  # no table yet?
			follower_table = []
			for i in range(defaults.TIME_TABLE_SIZE):  # for each entry slot
				follower_table.append(-1)  # per default nothing allowed

		# create ruleset mask
		# just a dummy for now, creates a fully packed ruleset
		ruleset_table = []
		for i in range(defaults.TIME_TABLE_SIZE):  # foreach entry slot
			ruleset_table.append(True)  # per default all set

		for i in range(defaults.TIME_TABLE_SIZE):  # for each entry slot
			if ruleset_table[i]:  # if the ruleset allows access, then
				sponsor_ttl = sponsor_table[i]
				if sponsor_ttl > 0:
					new_ttl = sponsor_ttl-1  # we reduce the ttl by 1
					# does the new ttl improve the depth level?
					if follower_table[i] < new_ttl:
						follower_table[i] = new_ttl
		return follower_table

	def garbage_collection(self, old_user_table):
		''' cleans up user and time plan tables

		as this might be time consuming, it's placed in a procedure
		which could be called by a seperate clean-up thread
		'''
		self.mutex.acquire()
		new_user_table = {}
		# admins are always walid
		admin_list = self.store.get_admin_ids()
		for admin in admin_list:
			new_user_table[admin] = {'user': self.users['users'][admin]
									 ['user'], 'time_table': self.create_full_time_table()}
		if not self.users['timetables']:
			self.mutex.release()
			return
		for user_id in self.users['timetables']:
			for time_table_id in self.users['timetables'][user_id]:
				if self.time_table_is_active(self.users['timetables'][user_id][time_table_id]):
					for follower_id in self.users['timetables'][user_id][time_table_id]['users']:
						# the date is set, so we don't handle this user here
						if self.users['timetables'][user_id][time_table_id]['users'][follower_id]:
							continue
						if not follower_id in new_user_table:
							new_user_table[follower_id] = {
								'user': self.users['users'][follower_id]['user'], 'time_table': None}
		'''and now we calculate the allowance, starting with the admin users and repeating the loop,
		until all valid users have got their time table derivated from their sponsors

		That might give a faulty result in the rare case that two users have invited each other cross-over.
		might this give a faulty time table?

		'''
		something_has_changed = True
		while something_has_changed:
			something_has_changed = False
			for user_id in self.users['timetables']:
				# the user has a time table, so he's either a admin or another already validated user
				if new_user_table[user_id]['time_table'] != None:
					for time_table_id in self.users['timetables'][user_id]:
						if self.time_table_is_active(self.users['timetables'][user_id][time_table_id]):
							for follower_id in self.users['timetables'][user_id][time_table_id]['users']:
								# there is no date set, so the follower is active
								if not self.users['timetables'][user_id][time_table_id]['users'][follower_id]:
									# did this user already had a time table before?
									if not new_user_table[follower_id]['time_table']:
										something_has_changed = True
									new_user_table[follower_id]['time_table'] = self.calculate_follower_time_table(
										new_user_table[user_id]['time_table'], None, new_user_table[follower_id]['time_table'])

		self.users['users'] = new_user_table
		delta_users = []
		for user_id, user in new_user_table.items():
			if not user_id in old_user_table:
				delta_users.append(user)
		for user_id, user in old_user_table.items():
			if not user_id in new_user_table:
				delta_users.append(user)
		try:
			self.store.write_users()
		finally:
			self.mutex.release()
		return delta_users

	def delete_user_by_id(self, current_user, delete_user_id):
		if current_user["user_id"] in self.users['timetables']:
			# for later enhancements. Actual there's only the standard id '1'
			for id in self.users['timetables'][current_user["user_id"]]:
				if delete_user_id in self.users['timetables'][current_user["user_id"]][id]['users']:
					# if a deletion date is not already set
					if not self.users['timetables'][current_user["user_id"]][id]['users'][delete_user_id]:
						self.users['timetables'][current_user["user_id"]
												 ][id]['users'][delete_user_id] = self.get_unix_timestamp()
		return self.garbage_collection(self.users['users'].copy())

	def user_info_by_id(self, user_id):
		if not user_id in self.users['users']:
			return None
		return self.users['users'][user_id]['user']

	def requestOTP(self, user):
		''' gets a unique one time password string'''

		with self.queue.mutex:
			self.queue.queue.clear()
		self.smart_home_interface.emit("otprequest", user)
		valid_time = 0
		msg_text = ""
		otp_type = 'qrcode'
		stringLength = 10
		otp = ''
		"""Generate a secure random string of letters, digits and special characters """
		password_characters = string.ascii_letters + string.digits + string.punctuation
		try:
			data = self.queue.get(block=True, timeout=2.0)
			print(data)
			if data['config']['result'] == True:
				valid_time = data['config']['valid_time']
				msg_text = data['config']['msg']
				otp_type = data['config']['type']
				if data['config']['type'] != 'qrcode':
					password_characters = data['config']['keypadchars']
				otp = ''.join(secrets.choice(password_characters)
							  for i in range(stringLength))
				self.current_tokens[otp] = datetime.datetime.now().timestamp(
				)+valid_time  # store, until when the token shall be valid
			else:
				msg_text = data['config']['msg']
		except:
			pass

		return {'otp': otp, 'valid_time': valid_time, 'msg': msg_text, 'type': otp_type}

	def validate_token(self, token):
		# first delete any old left-over
		print('token:', token)
		to_del = []
		now = datetime.datetime.now().timestamp()
		for old_token, timestp in self.current_tokens.items():
			if timestp + 5 * 60 < now:  # is the token expired more as 5 mins ago?
				to_del.append(old_token)
		for old_token in to_del:
			del(self.current_tokens[old_token])
		if not token in self.current_tokens:
			return False
		timestp = self.current_tokens[token]
		if timestp < now:  # is the token expired already?
			return False
		return True

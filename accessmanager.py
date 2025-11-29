#!/usr/bin/env python
# -*- coding: utf-8 -*-

import string
import secrets
import datetime
import queue
from threading import Thread, Lock
import defaults
import idcard
import zuullogger

logger = zuullogger.getLogger(__name__)


class AccessManager:
	'''contains all the function around user add & deletes, permissions etc.
	'''

	def __init__(self, modref, restart_function):
		''' handles incoming websocket messages

		Args:
		modref (:obj:`obj`): object containing references to the other program modules
		restart_function (:func:`function`): calback function to call when the program shall be restarted
		'''

		self.modref = modref
		self.mutex = Lock()  # prepare lock for atomar data changes
		self.users = self.modref.store.get_users()
		self.queue = queue.Queue()  # queue to receive ansers from websocket
		self.restart_function = restart_function
		self.smart_home_interface = modref.server
		# initial build of internal data tables
		self.garbage_collection(self.users['users'].copy())
		self.current_tokens = {}  # list of actual valid OTP token

	def msg(self, data, ws_user):
		''' handles incoming websocket messages

		Args:
		data (:obj:`obj`): data object
						type (:obj:`str`) : type of data
						config (:obj:`obj`): various data
		ws_user (:obj:`boolean`): websocket client object, needed to reply on messages
		'''

		if data['type'] == 'ac_otprequest':
			# answer received from websocket (in websocket context), put in queue for further processing
			self.queue.put(data)
		if data['type'] == 'ac_newconfig':
			# new config data received from Web UI
			self.write_config(data['config'])
		# token received from websocket, test on valid and return feedback to websocket
		if data['type'] == 'ac_tokenquery':
			ws_user.ws.emit(
				"tokenstate", {'valid': self.validate_token(data['config']['token']), 'msg':data['config']})

	def write_config(self, data):
		''' stores changed config data on disk

		Args:
		data (:obj:`obj`): new config data
		'''
		current_password=self.modref.store.read_config_value('current_password')
		if not current_password==data['current_password']:
			logger.debug("wrong password {0}".format(data['current_password']))
			return
		valid_fields = self.modref.store.config_keys()
		for key in valid_fields:  # copy only the allowed fields
			### if we have a password, then the token should not be changed through
			# the UI because of the actual poor implementation of the password handling
			if current_password and key=='messenger_token':
				continue
			if key in data:
				logger.debug("new config {0} {1}".format(key, repr(data[key])))
				self.modref.store.write_config_value(key, data[key], True)
		self.modref.store.create_new_admins_if_any()
		self.modref.store.save_config()
		if self.restart_function:  # restart bot
			self.restart_function()

	def dummy(self, user):
		''' empty procedure for websocket connect/disconnect handler
		'''
		pass

	def user_info(self, user):
		''' check user existance and updates user data

		Args:
		user (:obj:`user`): a user object

		Return:
		user object, if known, otherways None
		'''

		user_ref = self.user_info_by_id(user["user_id"])
		if user_ref:  # update the user with the latest just received data
			self.users['users'][user["user_id"]]['user'] = user
			return self.users['users'][user["user_id"]]['user']
		else:
			return user_ref

	def user_id(self, user):
		''' getter for user id

		Args:
		user (:user:`obj`): a user object

		Return:
		user id
		'''

		return user["user_id"]

	def user_is_active(self, user):
		'''returns a user only if he exists and is active

		Args:
		user (:user:`obj`): a user object

		Return:
		user object, if active, otherways None
		'''

		user_ref = self.user_info_by_id(user["user_id"])
		if user_ref:  # update the user with the latest just received data
			self.users['users'][user["user_id"]]['user'] = user
			# return user if user is active
			if self.users['users'][user["user_id"]]['time_table']:
				return user_ref
		return None

	def user_is_follower(self, current_user, active_user, time_table_id='1'):
		''' returns true if the user has no deletion time set

		Args:
		current_user (:user:`obj`): a user object
		active_user (:user:`obj`): a user object
		time_table_id (:str:`str`): id of current_user time_table, actual always '1'

		Return:
		Boolean
		'''

		# does the current user already have lend some keys?
		if not current_user["user_id"] in self.users['timetables']:
			return False
		if not active_user["user_id"] in self.users['timetables'][current_user["user_id"]][time_table_id]['users']:
			return False
		return self.users['timetables'][current_user["user_id"]][time_table_id]['users'][active_user["user_id"]] == None

	def user_can_lend(self, user):
		''' returns true if the user is allowed to lend his key further

		Args:
		user (:user:`obj`): a user object

		Return:
		Boolean
		'''

		for depth in self.users['users'][user["user_id"]]['time_table']:
			if depth > 0:
				return True
		return False

	def add_user(self, current_user, new_user, time_table_id='1'):
		'''Add a new user to the database

		Args:
		current_user (:user:`obj`): a user object
		new_user (:user:`obj`): a user object
		time_table_id (:str:`str`): id of current_user time_table, actual always '1'

		Return:
		list containing all user which have been added or deleted by this operation
		'''

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
				time_table_id: {'users': {}, 'deletion_timestamp': None}}
		# set the deletion date to None
		self.users['timetables'][current_user["user_id"]
								 ][time_table_id]['users'][new_user["user_id"]] = None
		return self.garbage_collection(old_user_table)

	def get_follower_list(self, sponsor_user, time_table_id='1'):
		'''creates a list of active followers of sponsor_user

		Args:
		sponsor_user (:user:`obj`): a user object
		time_table_id (:str:`str`): id of current_user time_table, actual always '1'

		Return:
		list containing all active follower users of sponsor_user
		'''

		res = []
		if sponsor_user["user_id"] in self.users['timetables']:
			# for later enhancements. Actual there's only the standard id '1'
			for follower_id in self.users['timetables'][sponsor_user["user_id"]][time_table_id]['users']:
				# if a deletion date is not already set
				if not self.users['timetables'][sponsor_user["user_id"]][time_table_id]['users'][follower_id]:
					res.append({'text': "{0} {1}".format(self.users['users'][follower_id]['user']['first_name'], self.users['users'][follower_id]['user']['last_name']),
								"user_id": follower_id})
		return res

	def get_sponsor_list(self, follower_user, time_table_id='1'):
		'''creates a list of sponsors of follower_user

		Args:
		follower_user (:user:`obj`): a user object
		time_table_id (:str:`str`): id of current_user time_table, actual always '1'

		Return:
		list containing all sponsors users of follower_user
		'''

		res = []
		follower_id = follower_user["user_id"]
		for sponsor_user_id in self.users['timetables']:
			for time_table in self.users['timetables'][sponsor_user_id].values():
				# important: users can also return keys out of inactive time tables, so we don't check if the table is active
				# no deletion date set
				if follower_id in time_table['users'] and not time_table['users'][follower_id]:
					res.append({'text': "{0} {1}".format(self.users['users'][sponsor_user_id]['user']['first_name'], self.users['users'][sponsor_user_id]['user']['last_name']),
								"user_id": sponsor_user_id})
		return res

	def get_unix_timestamp(self):
		'''return unix timestamp

		Return:
		unix timestamp as float
		'''

		return datetime.datetime.utcnow().timestamp()

	def time_table_is_active(self, time_table):
		''' returns the active state of the time table

		Args:
		time_table (:list:`obj`): a time table dict
		Return:
		Boolean
		'''

		if not time_table:
			return False
		# as time tables are not implemented yet, we check only the deletion data

		if time_table["deletion_timestamp"]:
			# older as  defaults.DELETE_AFTER_DAYS days
			if time_table["deletion_timestamp"] < self.get_unix_timestamp - 60 * 60 * 24 * defaults.DELETE_AFTER_DAYS:
				return False
		return True

	def calculate_follower_time_table(self, sponsor_table, ruleset, follower_table):
		''' overlays time tables

		this routine takes a follower_table and add all new sponsor_table permissions, if there is something to add
		it returnes the potentially amed follower_table

		Args:
		sponsor_table (:time_table:`dict`): a time table dict
		time_table (:obj:`obj`): ? not used yet
		follower_table (:time_table:`dict`): a time table dict
		Return:
		follower_table (:time_table:`dict`): a time table dict
		'''

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

		Args:
		old_user_table (:obj:`obj`): hash containing all active users as copy

		Return:
		list containing all user which have been added or deleted by this operation
		'''

		self.mutex.acquire()  # avoid thread interfearence
		new_user_table = {}
		# admins are always walid
		admin_list = self.modref.store.get_admin_ids()
		for admin in admin_list:
			new_user_table[admin] = {'user': self.users['users'][admin]
									 ['user'], 'time_table': self.modref.store.create_full_time_table()}
			# after startup the admins do not have a valid full time table, so we correct this here
			if not self.users['users'][admin]['time_table']:
				self.users['users'][admin]['time_table'] = self.modref.store.create_full_time_table()

		for user_id in self.users['timetables']:  # go through all sponsor users
			# go through all the users time_tables
			for time_table_id in self.users['timetables'][user_id]:
				# if active,
				if self.time_table_is_active(self.users['timetables'][user_id][time_table_id]):
					# go through all followers
					for follower_id in self.users['timetables'][user_id][time_table_id]['users']:
						# copy of all included followers into the new user table
						if not follower_id in new_user_table:  # if no deletion datetime is set, then
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
				if user_id in new_user_table and new_user_table[user_id]['time_table'] != None:
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

		# Reminder: If a users ['time_table'] is None, then the user is still anywhere in a time plan, but not avtive anymore

		# the new_user_table contains now all users, so it replaces the original global table
		self.users['users'] = new_user_table

		# now we prepare to identify the user add & deletes
		delta_users = []
		for user_id, user in new_user_table.items():
			if not user_id in old_user_table or user['time_table'] != None and old_user_table[user_id]['time_table'] == None:
				delta_users.append(user)
		for user_id, user in old_user_table.items():
			if not user_id in new_user_table or user['time_table'] != None and new_user_table[user_id]['time_table'] == None:
				delta_users.append(user)
		# finally we store the new calculated user data
		try:
			self.modref.store.write_users()
		finally:
			# release the mutex lock
			self.mutex.release()
		# and return the add/delete list
		return delta_users

	def delete_user_by_id(self, current_user_id, delete_user_id):
		''' makes a user inactive by set his deletion date in the follower table

		Args:
		current_user_id (:str:`str`): id of user who wants to delete
		delete_user_id (:str:`str`): id of user who should be delete

		Return:
		list containing all user which have been added or deleted by this operation
		'''

		if current_user_id in self.users['timetables']:
			# for later enhancements. Actual there's only the standard id '1'
			for id in self.users['timetables'][current_user_id]:
				if delete_user_id in self.users['timetables'][current_user_id][id]['users']:
					# if a deletion date is not already set
					if not self.users['timetables'][current_user_id][id]['users'][delete_user_id]:
						self.users['timetables'][current_user_id
												 ][id]['users'][delete_user_id] = self.get_unix_timestamp()
		return self.garbage_collection(self.users['users'].copy())

	def user_info_by_id(self, user_id):
		''' finds a user by his id

		Args:
		user_id (:str:`str`): id of user to find

		Return:
		user if found, otherways None
		'''

		if not user_id in self.users['users']:
			return None
		return self.users['users'][user_id]['user']

	def requestOTP(self, user):
		''' gets a unique one time password string

		returns an object containing a OTP (if permitted from Smart Home),
		how long it should be valid, optional message

		Args:
		user (:user:`obj`): user data

		Return:
		object containing
				an OTP string (if permitted from Smart Home),
				the OTP type (qrcode or others)
				how long it should be valid in secs
				an optional message
		'''

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
			data = self.queue.get(
				block=True, timeout=defaults.SMART_HOME_TIMEOUT)
			logger.debug(
				'data received from smart home {0}'.format(repr(data)))
			if data['config']['result'] == True:
				valid_time = data['config']['valid_time']
				msg_text = data['config']['msg']
				otp_type = data['config']['type']
				stringLength = data['config']['length']
				if data['config']['type'] != 'qrcode':
					password_characters = data['config']['keypadchars']
				password_characters = password_characters.replace("\"", "").replace(
					"\\", "").replace(":", "")  # everthing but without " and :"

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
		''' checks, if a received token string is either a servive token or a normal one
		Args:
		token (:str:`str`): token string

		Return:
		boolean True if valid
		'''

		# first delete any old left-over
		logger.debug('token: {0}'.format(token))
		to_del = []
		now = datetime.datetime.now().timestamp()
		for old_token, timestp in self.current_tokens.items():
			if timestp + 5 * 60 < now:  # is the token expired more as 5 mins ago?
				to_del.append(old_token)
		for old_token in to_del:
			del(self.current_tokens[old_token])

		# is is a service token?
		if token[:2] == "zm" and ':' in token:  # is is a service token?
			return idcard.verify_message(token.split(':')[1:], self.modref)
		if not token in self.current_tokens:
			return False
		timestp = self.current_tokens[token]
		if timestp < now:  # is the token expired already?
			return False
		return True

	def request_id_card(self, user, receiver, botname):
		''' generates a service token
		Args:
		user (:str:`str`): user, who has requested the service token
		receiver (:str:`str`): bot name the token shall be made for
		botname (:str:`str`): the own bot name

		Return:
		string  token string
		'''

		token = idcard.get_id_card_string(
			self.modref.store, str(self.user_id(user)), receiver, botname)
		logger.debug('generated token: {0}'.format(token))
		return "zm:"+token

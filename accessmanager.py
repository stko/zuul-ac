#!/usr/bin/env python
# -*- coding: utf-8 -*-

import string
import secrets
import datetime

class AccessManager:

	def __init__(self, store):
		self.store=store
		self.users=store.get_users()
		self.garbage_collection()

	def msg(self,data, ws_user):
		print(data["data"]["token"])
		ws_user.ws.emit("test",data)

	def dummy(self, user):
		pass

	def user_info(self,user):
		user_ref=self.user_info_by_id(user["user_id"])
		if user_ref: # update the user with the latest just received data
			self.users['users'][user["user_id"]]['user']=user
			return self.users['users'][user["user_id"]]['user']
		else:
			return user_ref

	def user_id(self,user):
		return user["user_id"]

	def is_user_active(self,current_user,active_user,time_table_id='1'):
		''' returns true if the user has no deletion time set'''
		# does the current user already have lend some keys?
		if not current_user["user_id"] in self.users['timetables']:
			return False
		if not active_user["user_id"] in self.users['timetables'][current_user["user_id"]][time_table_id]['users']:
			return False
		return self.users['timetables'][current_user["user_id"]][time_table_id]['users'][active_user["user_id"]] == None

	def add_user(self,current_user,new_user):
		'''Add a new user to the database'''
		self.users['users'][new_user["user_id"]]={'user':new_user}
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
			self.users['timetables'][current_user["user_id"]]={'1':{'users':{},'deletion_timestamp':None}}
		self.users['timetables'][current_user["user_id"]]['1']['users'][new_user["user_id"]]=None # set the deletion date to None
		self.store.write_users()

	def get_user_list(self):
		res=[]
		for user in self.users['users'].values():
			if user:
				res.append({'text':user['first_name'],"user_id":user["user_id"]})
		res=[
			{'text':'Nur Zhang','user_id':'id_1'},
			{'text':'Kain Lister','user_id':'id_2'},
			{'text':'Britany Brown','user_id':'id_3'},
			{'text':'Benas Cochran','user_id':'id_4'},
			{'text':'Jevan Roberts','user_id':'id_5'},
			{'text':'Pierce Bonilla','user_id':'id_6'},
			{'text':'Delilah Perry','user_id':'id_7'},
			{'text':'Chelsy Thorne','user_id':'id_8'},
			{'text':'Rahul Drummond','user_id':'id_9'},
			{'text':'Hebe Naylor','user_id':'id_10'},
		]


		return res

	def get_unix_timestamp(self):
		return datetime.datetime.utcnow().timestamp()

	def time_table_is_active(self, time_table):
		''' returns the active state of the time table'''
		
		if not time_table:
			return False
		# as time tables are not implemented yet, we check only the deletion data
		
		if time_table["deletion_timestamp"]:
			if time_table["deletion_timestamp"] < self.get_unix_timestamp -  60 * 60 * 24 * 30: #older as 30 days
				return False
		return True

	def garbage_collection(self):
		''' cleans up user and time plan tables

		as this might be time consuming, it's placed in a procedure
		which could be called by a seperate clean-up thread
		'''
		new_user_table={}
		# admins are always walid
		for admin in self.store.get_admin_ids():
			new_user_table[admin]={'user':self.users['users'][admin]['user'],'time_table':None}
		if not self.users['timetables']:
			return
		for user_id in self.users['timetables']:
			for time_table_id in self.users['timetables'][user_id]:
				if self.time_table_is_active(self.users['timetables'][user_id][time_table_id]):
					for follower_id in self.users['timetables'][user_id][time_table_id]['users']:
						if not follower_id in new_user_table:
							new_user_table[follower_id]={'user':self.users['users'][follower_id]['user'],'time_table':None}
		self.users['users']=new_user_table
		self.store.write_users()

	def delete_user_by_id(self,current_user,delete_user_id):
		if current_user["user_id"] in self.users['timetables']:
			for id in self.users['timetables'][current_user["user_id"]]: # for later enhancements. Actual there's only the standard id '1'
				if delete_user_id in self.users['timetables'][current_user["user_id"]][id]['users']:
					if not self.users['timetables'][current_user["user_id"]][id]['users'][delete_user_id]: # if a deletion date is not already set
						self.users['timetables'][current_user["user_id"]][id]['users'][delete_user_id]=self.get_unix_timestamp()
		self.garbage_collection()

	def user_info_by_id(self,user_id):
		if not user_id in self.users['users']:
			return None
		return self.users['users'][user_id]['user']

	def requestOTP(self,user):
		''' gets a unique one time password string'''

		stringLength=10
		"""Generate a secure random string of letters, digits and special characters """
		password_characters = string.ascii_letters + string.digits + string.punctuation
		otp= ''.join(secrets.choice(password_characters) for i in range(stringLength))
		return otp , 60




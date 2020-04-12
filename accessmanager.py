#!/usr/bin/env python
# -*- coding: utf-8 -*-

import string
import secrets

class AccessManager:

	def __init__(self, store):
		self.store=store
		self.users=store.get_users()

	def msg(self,data, user):
		print(data["data"]["token"])
		user.ws.emit("test",data)

	def dummy(self, user):
		pass

	def user_info(self,user):
		return self.user_info_by_id(user.user_id)

	def user_id(self,user):
		return user.user_id

	def add_user(self,user):
		self.users['users'][user.user_id]=user
		self.store.write_users()

	def delete_user_by_id(self,user_id):
		if  user_id in self.users['users']:
			del(self.users['users'][user_id])
			self.store.write_users()

	def user_info_by_id(self,user_id):
		if not user_id in self.users['users']:
			return None
		return self.users['users'][user_id]

	def requestOTP(self,user):
		''' gets a unique one time password string'''

		stringLength=10
		"""Generate a secure random string of letters, digits and special characters """
		password_characters = string.ascii_letters + string.digits + string.punctuation
		otp= ''.join(secrets.choice(password_characters) for i in range(stringLength))
		return otp




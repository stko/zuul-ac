#!/usr/bin/env python
# -*- coding: utf-8 -*-

class User:
	def __init__(self, first_name, last_name, id , language):
		self.first_name= first_name
		self.last_name = last_name
		self.user_id   = str(id)
		self.language  = language
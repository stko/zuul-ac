#!/usr/bin/env python
# -*- coding: utf-8 -*-


def msg(data, user):
	print(data["data"]["token"])
	user.ws.emit("test",data)

def dummy(user):
	pass
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# https://inventwithpython.com/blog/2014/12/20/translate-your-python-3-program-with-the-gettext-module/
'''
import gettext
localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'locale')
translate = gettext.translation('guess', localedir, fallback=True)
_ = translate.gettext
'''

def gettext(text):
	#global translate
	#return translate.gettext(text)
	return text

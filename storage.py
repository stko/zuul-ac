#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import zuullogger
import translate

_ = translate.gettext

logger = zuullogger.getLogger(__name__)
config = {}
config_file_name='config.json'

try:
	with open(config_file_name) as json_file:
		config = json.load(json_file)

except:
	logger.warning(_("could'nt load config file {0}").format(config_file_name))

def read_config_value(value):
	if value in config:
		return config[value]
	return None


def write_config_value(key, value):
	global config, config_file_name
	config[key]=value
	with open(config_file_name, 'w') as outfile:
		json.dump(config, outfile)
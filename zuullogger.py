#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def getLogger(name):
	return logging.getLogger(name)

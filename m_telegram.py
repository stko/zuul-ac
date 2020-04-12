#!/usr/bin/env python
# -*- coding: utf-8 -*-


from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import qrcode
import string
import secrets
import zuullogger
from user import User
from io import BytesIO

import translate

_ = translate.gettext
logger = zuullogger.getLogger(__name__)



class ZuulMessengerPlugin:
	'''
	implements the connection to the telegram messenger infrastructure
	'''

	def clear_keyboard(self):
		''' initialize the virtual keyboard'''

		self.keyboard = [[]]
		self.keyboard_functions = {}

	def add_keyboard_item(self, text, callback_data, callback_function, new_row):
		''' builds dynamically virtual keyboards

		Args:
		text  (:obj:`str`): The text of the button

		callback_data (:obj:`str`): The value reported back to the keyboard handler

		callback_function (:func:`func`): the event handler for this button

		new_row (:obj:`bool`): layout instruction. Generates a new button row if True
		'''

		if self.keyboard and new_row:
			self.keyboard.append([])
		last_row = self.keyboard[-1]
		last_row.append(InlineKeyboardButton(
			text, callback_data=callback_data))
		self.keyboard_functions[callback_data] = callback_function

	def compile_keyboard(self):
		''' translates keyboard layout into internal representation '''

		return InlineKeyboardMarkup(self.keyboard)

	def execute_keyboard_callback(self, update, context, query):
		''' calls button specific event handler

		the event handler is choosen by the callback_data and then called with
		the callback_data 

		Args:
		callback_data (:obj:`str`): The value reported back to the keyboard handler
		'''


		if not query.data in self.keyboard_functions:
			print("ilegal callback_data")
			return None
		return self.keyboard_functions[query.data]( update, context, query)

	def __init__(self, messenger_token, access_manager):
		"""Start the bot."""

		# Create the Updater and pass it your bot's token.
		# Make sure to set use_context=True to use the new context based callbacks
		# Post version 12 this will no longer be necessary
		updater = Updater(messenger_token, use_context=True)
		self.access_manager = access_manager
		self.keyboard = [[]]
		self.keyboard_functions = {}
		self.new_contact = None

		self.last_shared_user = None
		# Get the dispatcher to register handlers
		dp = updater.dispatcher

		# on different commands - answer in Telegram
		dp.add_handler(CommandHandler("start", self.new_pin))
		dp.add_handler(CommandHandler("help", self.help))
		dp.add_handler(CallbackQueryHandler(self.button,pass_update_queue=True))
		dp.add_handler(MessageHandler(Filters.contact, self.share_contact))

		# on noncommand i.e message - echo the message on Telegram
		dp.add_handler(MessageHandler(Filters.text, self.echo))

		# log all errors
		dp.add_error_handler(self.error)

		# Start the Bot
		updater.start_polling()

		# Run the bot until you press Ctrl-C or the process receives SIGINT,
		# SIGTERM or SIGABRT. This should be used most of the time, since
		# start_polling() is non-blocking and will stop the bot gracefully.

		# updater.idle() can only be used in main thread
		# updater.idle()

	def user(self, update):
		'''filters the user data out of the update object'''
		chat_user = update.effective_user
		return User(chat_user.first_name, chat_user.last_name, chat_user.id, chat_user.
					language_code)

	def send_image(self, update,query):
		user = self.user(update)
		msg=self.select_message_source(update,query)

		qr = qrcode.QRCode(
			version=1,
			error_correction=qrcode.constants.ERROR_CORRECT_L,
			box_size=10,
			border=4,
		)
		qr.add_data(self.access_manager.requestOTP(user))
		qr.make(fit=True)

		img = qr.make_image(fill_color="black", back_color="white")

		bio = BytesIO()
		bio.name = 'image.jpeg'
		img.save(bio, 'PNG')
		bio.seek(0)

		msg.reply_text(
			_('Dieser Code ist 60 Sekunden gültig - Halte ihn einfach vor die Kamera, um die Tür zu öffnen'))
		#update.message.reply_photo( photo= open('qr-code.png', 'rb'))
		msg.reply_photo(photo=bio)
		msg.reply_text(
			_('Wenn Du einen neuen Code brauchst, schreib hier einfach irgend etwas'))

	# Define a few command handlers. These usually take the two arguments update and
	# context. Error handlers also receive the raised TelegramError object in error.

	def simple_keyboard_callback(self, callback_data):
		print("simple callback", callback_data)

	def select_message_source(self, update,query):
		if query:
			return query.message
		else:
			return update.message

	def new_pin(self, update, context):
		"""Send a pin instandly when the command /start is issued."""
		self.menu_new_pin(update, context, None)

	def menu_new_pin(self, update, context, query):
		"""Send a pin instandly"""
		msg=self.select_message_source(update,query)

		if self.access_manager.user_info(self.user(update))!=None: # known user?
			msg.reply_text(_('Hi!'))
			self.send_image(update,query)
		self.menu_main(update, context, query)

	def help(self, update, context):
		"""Send a message when the command /help is issued."""
		update.message.reply_text(_('Help!'))

	def add_follower_callback(self, update, context, query):
		'''adds a new user'''
		if self.new_contact:
			self.access_manager.add_user(self.new_contact)
		self.new_contact=None
		self.menu_main(update, context, query)

	def delete_follower_callback(self, update, context, query):
		'''deletes a user'''
		self.access_manager.delete_user_by_id(query.data)
		self.menu_main(update, context, query)

	def menu_main(self, update, context, query):
		msg=self.select_message_source(update,query)
		self.clear_keyboard()
		if self.access_manager.user_info(self.user(update)) != None: # known user?
			self.add_keyboard_item(_("New Pin"), "dummy",
								self.menu_new_pin, True)
			reply_markup = self.compile_keyboard()
			msg.reply_text(_('Your Choice?:'), reply_markup=reply_markup)

		else:
			msg.reply_text(
					_('unknown user!'), reply_markup=reply_markup)



	def add_follower(self, update, context,new_user):

		self.clear_keyboard()
		self.add_keyboard_item(_("Add"), "add",
							   self.add_follower_callback, True)
		self.add_keyboard_item(_("Main"), "goto_main",
							   self.menu_main, True)
		reply_markup = self.compile_keyboard()

		update.message.reply_text(
			_('Ok to add {0} {1}?:').format(new_user.first_name,new_user.last_name), reply_markup=reply_markup)


	def delete_follower(self, update, context,user):
		'''deletes a user'''
		self.clear_keyboard()
		self.add_keyboard_item(_("Delete"), self.access_manager.user_id(user),
							   self.delete_follower_callback, True)
		self.add_keyboard_item(_("Main"), "goto_main",
							   self.menu_main, True)
		reply_markup = self.compile_keyboard()

		update.message.reply_text(
			_('Ok to Delete {0} {1}?:').format(user.first_name,user.last_name), reply_markup=reply_markup)


	def share_contact(self, update, context):
		"""Checks, if a shared contact already exists"""
		self.new_contact = User(update.message.contact.first_name, update.message.contact.last_name,
									 update.message.contact.user_id, None)  # contacts don't have language codes
		print("contact", repr(self.new_contact))
		user_info = self.access_manager.user_info(self.new_contact)
		if user_info != None:
			self.delete_follower(update, context,user_info)
		else:
			self.add_follower(update, context,self.new_contact)



	def button(self, update, context):
		query = update.callback_query
		 # CallbackQueries need to be answered, even if no notification to the user is needed
		# Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
		query.answer()
		self.execute_keyboard_callback( update, context, query)
		#query.edit_message_text(text="Selected option: {}".format(query.data))

	def echo(self, update, context):
		"""Echo the user message."""
		update.message.reply_text(_("Du schriebst:")+update.message.text)
		print(update.message.text)
		self.menu_main(update, context, None)


	def error(self, update, context):
		"""Log Errors caused by Updates."""
		logger.warning('Update "%s" caused error "%s"', update, context.error)


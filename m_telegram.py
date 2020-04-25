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
# _ = translate.gettext
logger = zuullogger.getLogger(__name__)


class ZuulMessengerPlugin:
	'''
	implements the connection to the telegram messenger infrastructure
	'''

	def _(self, text):
		if self.current_user:
			return translate.gettext(text, self.current_user['language'])
		else:
			return text

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
		query (:obj:`str`): reference to the requested query. callback data is located in query.data
		'''

		if not query.data in self.keyboard_functions:
			print("ilegal callback_data")
			self.new_pin(update, context)
			return None
		return self.keyboard_functions[query.data](update, context, query)

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
		self.current_user = None
		# Get the dispatcher to register handlers
		dp = updater.dispatcher

		# on different commands - answer in Telegram
		dp.add_handler(CommandHandler("start", self.new_pin))
		dp.add_handler(CommandHandler("help", self.help))
		dp.add_handler(CallbackQueryHandler(
			self.button, pass_update_queue=True))
		# handler when user shares a contact
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
		print("user name:{0} {1}".format(
			chat_user.first_name, chat_user.last_name))
		return User(chat_user.first_name, chat_user.last_name, chat_user.id, chat_user.
					language_code)

	def send_image(self, update, query):
		user = self.user(update)
		msg = self.select_message_source(update, query)

		otp = self.access_manager.requestOTP(user)
		if otp['valid_time'] > 0:
			if otp['type'] == 'qrcode':
				qr = qrcode.QRCode(
					version=1,
					error_correction=qrcode.constants.ERROR_CORRECT_L,
					box_size=10,
					border=4,
				)
				qr.add_data(otp['otp'])
				qr.make(fit=True)

				img = qr.make_image(fill_color="black", back_color="white")

				bio = BytesIO()
				bio.name = 'image.jpeg'
				img.save(bio, 'PNG')
				bio.seek(0)
				if otp['msg']:
					msg_text = otp['msg']
				else:
					msg_text = 'This Pin is valid for {0} seconds - Just present it to the door camera to open the door'
				msg.reply_text(
					self._(msg_text).format(otp['valid_time'], otp['otp']))
				#update.message.reply_photo( photo= open('qr-code.png', 'rb'))
				msg.reply_photo(photo=bio)
			else:
				if otp['msg']:
					msg_text = otp['msg']
				else:
					msg_text = 'This Pin {1} is valid for {0} seconds'
				msg.reply_text(
					self._(msg_text).format(otp['valid_time'], otp['otp']))

		else:
			if otp['msg']:
				msg_text = otp['msg']
			else:
				msg_text = 'You won\'t let in just now. Please try again at another time'
			msg.reply_text(
				self._(msg_text))

	# Define a few command handlers. These usually take the two arguments update and
	# context. Error handlers also receive the raised TelegramError object in error.

	def simple_keyboard_callback(self, update, context, query):
		print("simple callback", query.data)

	def select_message_source(self, update, query):
		if query and query.message:
			return query.message
		else:
			if update.message:
				return update.message
			else:
				return update.effective_message

	def new_pin(self, update, context):
		"""Send a pin instandly when the command /start is issued."""
		self.menu_new_pin(update, context, None)

	def menu_new_pin(self, update, context, query):
		"""Send a pin instandly"""
		msg = self.select_message_source(update, query)

		# known user?
		self.current_user = self.access_manager.user_info(self.user(update))
		if self.current_user != None:
			self.send_image(update, query)
		self.menu_main(update, context, query)

	def menu_help(self, update, context, query):
		"""Send the docs URL"""
		msg = self.select_message_source(update, query)
		msg.reply_text(self._("https://github.com/stko/zuul-ac"))
		self.menu_main(update, context, query)

	def help(self, update, context):
		"""Send a message when the command /help is issued."""
		update.message.reply_text(self._('Go to the Online Manual'))
		self.menu_help(update, context, None)

	def add_follower_callback(self, update, context, query):
		'''adds a new user'''
		msg = self.select_message_source(update, query)
		if self.new_contact and self.current_user:
			changed_users = self.access_manager.add_user(
				self.current_user, self.new_contact)
			for user in changed_users:
				#context.bot.send_message(chat_id=user['user_id'], text=self._("You got a key. You can open the door now"))
				context.bot.send_message(chat_id='1137173018', text=self._("You got a key. You can open the door now"))
			msg.reply_text(self._('Key lend to {0} {1}').format(
				self.new_contact['first_name'], self.new_contact['last_name']))
		else:
			msg.reply_text(self._("Something went wrong"))
		self.new_contact = None
		self.menu_main(update, context, query)

	def delete_follower_callback(self, update, context, query):
		'''deletes a user'''
		msg = self.select_message_source(update, query)
		delete_user = self.access_manager.user_info_by_id(query.data)
		if delete_user and self.current_user:
			changed_users=self.access_manager.delete_user_by_id(
				self.current_user, query.data)
			for user in changed_users:
				#context.bot.send_message(chat_id=user['user_id'], text=self._("Your key was revoked. You can not open the door anymore"))
				context.bot.send_message(chat_id='1137173018', text=self._("Your key was revoked. You can not open the door anymore"))

			msg.reply_text(self._('Key brought back from {0} {1}').format(
				delete_user['first_name'], delete_user['last_name']))
		else:
			msg.reply_text(self._("Something went wrong"))
		self.menu_main(update, context, query)

	def delete_sponsor_callback(self, update, context, query):
		'''deletes a sponsor'''
		msg = self.select_message_source(update, query)
		delete_user = self.access_manager.user_info_by_id(query.data)
		if delete_user and self.current_user:
			self.access_manager.delete_user_by_id(
				query.data, self.current_user)
			msg.reply_text(self._('Key returned to {0} {1}').format(
				delete_user['first_name'], delete_user['last_name']))
		else:
			msg.reply_text(self._("Something went wrong"))
		self.menu_main(update, context, query)

	def delete_follower_by_list_item(self, update, context, query):
		'''deletes a user'''
		self.delete_follower(
			update, context, self.access_manager.user_info_by_id(query.data))

	def delete_sponsor_by_list_item(self, update, context, query):
		'''deletes a sponsor'''
		self.delete_sponsor(
			update, context, self.access_manager.user_info_by_id(query.data))

	def list_follower_callback(self, update, context, query):
		msg = self.select_message_source(update, query)
		self.last_follower_pos = self.fill_list(
			query.data, self.access_manager.get_follower_list, self.delete_follower_by_list_item, self.list_follower_callback)
		self.add_keyboard_item(self._('Commands'), "menu",
												   self.menu_menu, True)
		reply_markup = self.compile_keyboard()
		msg.reply_text(self._('Choose the Key to get back'),
					   reply_markup=reply_markup)

	def list_sponsor_callback(self, update, context, query):
		msg = self.select_message_source(update, query)
		self.last_follower_pos = self.fill_list(
			query.data, self.access_manager.get_sponsor_list, self.delete_sponsor_by_list_item, self.list_sponsor_callback)
		self.add_keyboard_item(self._('Commands'), "menu",
												   self.menu_menu, True)
		reply_markup = self.compile_keyboard()
		msg.reply_text(self._('Choose the Key to get back'),
					   reply_markup=reply_markup)

	def fill_list(self, last_pos, get_list, item_callback, list_callback):
		self.clear_keyboard()
		last_pos = int(last_pos)
		if last_pos < 0:  # a dirty trick, as we can't start all lists with the same starting index 0, as that crashes in the virtual keyboard generation, when all keyboard buttons would have the same index...
			last_pos = 0
		items_per_page = 5
		item_list = get_list(self.current_user)
		list_len = len(item_list)
		# calculate view
		for i in range(items_per_page):
			if (i+last_pos) < list_len:
				self.add_keyboard_item(item_list[i+last_pos]["text"], item_list[i+last_pos]["user_id"],
									   item_callback, True)
		if last_pos > 0:
			new_pos = last_pos-items_per_page
			if new_pos < 0:
				new_pos = 0
			self.add_keyboard_item('<', str(new_pos),
								   list_callback, True)
		else:
			self.add_keyboard_item('-', '0',
								   list_callback, True)
		if last_pos+items_per_page < list_len:
			self.add_keyboard_item('>', str(last_pos+items_per_page),
								   list_callback, False)
		else:
			self.add_keyboard_item('-', str(last_pos),
								   list_callback, False)

	def menu_menu(self, update, context, query):
		msg = self.select_message_source(update, query)
		self.clear_keyboard()
		self.add_keyboard_item(self._("Get lend Keys back"), "-1",  # the minus -1 is to make the index unique
							   self.list_follower_callback, True)
		self.add_keyboard_item(self._("Return borrowed Keys"), "-2",  # the minus -2 is to make the index unique
							   self.list_sponsor_callback, True)
		self.add_keyboard_item(self._("Help"), "help",
							   self.menu_help, True)
		self.add_keyboard_item(self._("Main Menu"), "goto_main",
							   self.menu_main, True)
		reply_markup = self.compile_keyboard()
		msg.reply_text(self._('Commands'), reply_markup=reply_markup)

	def menu_main(self, update, context, query):
		msg = self.select_message_source(update, query)
		self.clear_keyboard()
		# known user?
		self.current_user = self.access_manager.user_info(self.user(update))
		if self.current_user != None:
			text_info = self._('Main Menu')
			self.add_keyboard_item(self._("New Pin"), "dummy",
								   self.menu_new_pin, True)
			self.add_keyboard_item(self._("Commands"), "menu",
													   self.menu_menu, True)
		else:
			text_info = self._('Unknown User!')
			self.add_keyboard_item(self._("Help"), "help",
								   self.menu_help, True)

		reply_markup = self.compile_keyboard()
		msg.reply_text(text_info, reply_markup=reply_markup)

	def add_follower(self, update, context, new_user):

		self.clear_keyboard()
		self.add_keyboard_item(self._("Lend Key"), "add",
												   self.add_follower_callback, True)
		self.add_keyboard_item(self._('Main Menu'), "goto_main",
							   self.menu_main, True)
		reply_markup = self.compile_keyboard()

		update.message.reply_text(
			self._('Ok to lend the Key to {0} {1}?').format(new_user['first_name'], new_user['last_name']), reply_markup=reply_markup)

	def delete_follower(self, update, context, user):
		'''deletes a user'''
		self.clear_keyboard()
		self.add_keyboard_item(self._("Bring Back"), self.access_manager.user_id(user),
							   self.delete_follower_callback, True)
		self.add_keyboard_item(self._('Main Menu'), "goto_main",
							   self.menu_main, True)
		reply_markup = self.compile_keyboard()
		if update.message:
			msg = update.message
		else:
			msg = update.effective_message
		msg.reply_text(
			self._('Ok to bring back the key from {0} {1}?').format(user['first_name'], user['last_name']), reply_markup=reply_markup)

	def delete_sponsor(self, update, context, user):
		'''deletes a sponsor'''
		self.clear_keyboard()
		self.add_keyboard_item(self._("return"), self.access_manager.user_id(user),
							   self.delete_sponsor_callback, True)
		self.add_keyboard_item(self._('Main Menu'), "goto_main",
							   self.menu_main, True)
		reply_markup = self.compile_keyboard()
		if update.message:
			msg = update.message
		else:
			msg = update.effective_message
		msg.reply_text(
			self._('Ok to return the key to {0} {1}?').format(user['first_name'], user['last_name']), reply_markup=reply_markup)

	def share_contact(self, update, context):
		if update.message:
			msg = update.message
		else:
			msg = update.effective_message
		self.current_user = self.access_manager.user_info(self.user(update))

		"""Checks, if a shared contact already exists"""
		self.new_contact = User(update.message.contact.first_name, update.message.contact.last_name,
								update.message.contact.user_id, None)  # contacts don't have language codes
		user_info = self.access_manager.user_info(self.new_contact)
		if user_info != None:
			if self.access_manager.user_is_active(self.current_user, self.new_contact):
				self.delete_follower(update, context, user_info)
				return
		if self.access_manager.user_can_lend(self.current_user):
			self.add_follower(update, context, self.new_contact)
		else:
			msg.reply_text(	self._('You can not lend your key further'))



	def button(self, update, context):
		query = update.callback_query
		# CallbackQueries need to be answered, even if no notification to the user is needed
		# Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
		query.answer()
		self.execute_keyboard_callback(update, context, query)
		#query.edit_message_text(text="Selected option: {}".format(query.data))

	def echo(self, update, context):
		"""Echo the user message."""
		update.message.reply_text(self._("You wrote:")+update.message.text)
		print(update.message.text)
		self.menu_main(update, context, None)

	def error(self, update, context):
		"""Log Errors caused by Updates."""
		logger.warning('Update "%s" caused error "%s"', update, context.error)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, User
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ApplicationBuilder, ContextTypes

import qrcode
import string
import secrets
import asyncio
import zuullogger
from user import User
from io import BytesIO
import urllib

import translate

logger = zuullogger.getLogger(__name__)


class UserContext:
	''' object to hold all user relevant data of an incoming message.
			python-telegram-bot itself handles all incoming events in a global context,
			so we need a seperate object to store per user
	'''

	@classmethod
	def set_failback_menu(cls, new_pin):
		''' define what to do in case of an broken context
		'''

		cls.failback_menu = new_pin

	@classmethod
	def get_user_context(cls, update, context, query):
		''' Try to read user data and message context out of the incoming data.
		to store user data and read it again later, it uses the context.chat_data property

		Return:
		UserContext object
		'''

		if not 'user_context' in context.chat_data:
			context.chat_data['user_context'] = UserContext()
		user_context = context.chat_data['user_context']
		if query and query.message:
			user_context.msg = query.message
		else:
			if update.message:
				user_context.msg = update.message
			else:
				user_context.msg = update.effective_message
		if not user_context.user and update.effective_user:
			'''filters the user data out of the update object'''
			chat_user = update.effective_user
			user_context.user = User(chat_user.first_name, chat_user.last_name, chat_user.id, chat_user.
									 language_code)
			user_context.bot = context.bot
		return user_context

	def __init__(self):
		self.keyboard = [[]]
		self.keyboard_functions = {}
		self.new_contact = None
		self.user = None
		self.msg = None
		self.bot = None
		self.last_follower_pos = -1

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

	async def execute_keyboard_callback(self, update, context, query):
		''' calls button specific event handler

		the event handler is choosen by the callback_data and then called with
		the callback_data 

		Args:
		query (:obj:`str`): reference to the requested query. callback data is located in query.data
		'''

		if not query.data in self.keyboard_functions:
			await UserContext.failback_menu(update, context)
			return None
		return await self.keyboard_functions[query.data](update, context, query)

	def _(self, text):
		''' translates text based on user specific language settings
		'''
		if self.user:
			return translate.gettext(text, self.user['language'])
		else:
			return text


class ZuulMessengerPlugin:
	'''
	implements the connection to the telegram messenger infrastructure
	'''

	def __init__(self, messenger_token, access_manager):
		"""Start the bot."""

		""" 		
		# Create the Updater and pass it your bot's token.
		# Make sure to set use_context=True to use the new context based callbacks
		# Post version 12 this will no longer be necessary
		self.updater = Updater(messenger_token, use_context=True)
		# Get the dispatcher to register handlers
		dp = self.updater.dispatcher
 		"""	
		self.application = ApplicationBuilder().token(messenger_token).build()

		self.access_manager = access_manager

		# on different commands - answer in Telegram
		# will be automatically called at new connection
		self.application.add_handler(CommandHandler("start", self.new_pin))
		self.application.add_handler(CommandHandler("help", self.help))
		self.application.add_handler(CallbackQueryHandler(
			self.button))
		# handler when user shares a contact
		self.application.add_handler(MessageHandler(filters.CONTACT , self.share_contact))

		# set the failback menu, in case something goes wrong
		UserContext.set_failback_menu(self.new_pin)

		# on noncommand i.e message - echo the message on Telegram
		self.application.add_handler(MessageHandler(filters.TEXT, self.echo))

		# log all errors
		self.application.add_error_handler(self.error)

		# Start the Bot
		##self.application.run_polling()

		# Run the bot until you press Ctrl-C or the process receives SIGINT,
		# SIGTERM or SIGABRT. This should be used most of the time, since
		# start_polling() is non-blocking and will stop the bot gracefully.

		# updater.idle() can only be used in main thread
		# updater.idle()

	def run(self):

		# Start the Bot
		self.application.run_polling()

	# https://github.com/python-telegram-bot/python-telegram-bot/issues/801#issuecomment-323778248
	def shutdown(self):
		self.application.shutdown()
		#self.application.is_idle = False

	def user(self, update):
		'''filters the user data out of the update object'''
		chat_user = update.effective_user
		return User(chat_user.first_name, chat_user.last_name, chat_user.id, chat_user.
					language_code)

	async def myself(self) -> User :
		'''returns a user object about the bot itself
		'''
		user = await self.application.bot.get_me()
		return user

	async def send_pin_code(self, update, context, query):
		''' requests OneTimePassword (OTP) from access_manager and
		sends it to the user
		'''

		user_context = UserContext.get_user_context(update, context, query)
		otp = self.access_manager.requestOTP(user_context.user)
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
					msg_text = user_context._(
						'This Pin is valid for {0} seconds - Just present it to the door camera to open the door')
				await user_context.msg.reply_text(
					msg_text.format(otp['valid_time'], otp['otp']))
				#update.message.reply_photo( photo= open('qr-code.png', 'rb'))
				await user_context.msg.reply_photo(photo=bio)
			else:
				if otp['msg']:
					msg_text = otp['msg']
				else:
					msg_text = user_context._(
						'This Pin {1} is valid for {0} seconds')
				await user_context.msg.reply_text(
					msg_text.format(otp['valid_time'], otp['otp']))

		else:
			if otp['msg']:
				msg_text = otp['msg']
			else:
				msg_text = user_context._(
					'You won\'t let in just now. Please try again at another time')
			await user_context.msg.reply_text(msg_text)

	# Define a few command handlers. These usually take the two arguments update and
	# context. Error handlers also receive the raised TelegramError object in error.

	async def new_pin(self, update, context):
		"""Send a pin instandly when the command /start is issued."""
		await self.menu_new_pin(update, context, None)

	async def menu_new_pin(self, update, context, query):
		"""Send a pin instandly"""
		user_context = UserContext.get_user_context(update, context, query)
		# known user?
		if self.access_manager.user_is_active(
				user_context.user) != None:
				  # in case the /start command contains another bot name to make a certificate QRCode for it
			if context.args:
				self.create_certificate(
					user_context, urllib.parse.unquote(context.args[0]))
			else:
				await self.send_pin_code(update, context, query)
		await self.menu_main(update, context, query)

	async def menu_help(self, update, context, query):
		"""Send the docs URL"""
		user_context = UserContext.get_user_context(update, context, query)
		await user_context.msg.reply_text(
			user_context._("https://stko.github.io/zuul-ac/"))
		await self.menu_main(update, context, query)

	async def help(self, update, context):
		"""Send a message when the command /help is issued."""
		user_context = UserContext.get_user_context(update, context, None)
		await update.message.reply_text(user_context._('Go to the Online Manual'))
		self.menu_help(update, context, None)

	async def create_certificate(self, user_context, door_bot_name):
		"""Send acertificate."""
		own_bot_username = self.myself().name
		id_card = self.access_manager.request_id_card(
			user_context.user, door_bot_name, own_bot_username)
		qr = qrcode.QRCode(
			version=1,
			error_correction=qrcode.constants.ERROR_CORRECT_L,
			box_size=10,
			border=4,
		)
		qr.add_data(id_card)
		qr.make(fit=True)
		img = qr.make_image(fill_color="black", back_color="white")
		bio = BytesIO()
		bio.name = 'image.jpeg'
		img.save(bio, 'PNG')
		bio.seek(0)
		msg_text = user_context._(
			'Digital ID Card from {0}- Just present it to the door camera to open the door').format(own_bot_username)
		await user_context.msg.reply_text(
			msg_text)
		await user_context.msg.reply_photo(photo=bio)

	async def add_follower_callback(self, update, context, query):
		'''adds a new user'''
		user_context = UserContext.get_user_context(update, context, query)
		if user_context.new_contact and user_context.user:
			changed_users = self.access_manager.add_user(  # add the contact as new follower
				user_context.user, user_context.new_contact)
			keyboard = [[InlineKeyboardButton(
				'🚪'+self.myself().first_name, callback_data='main')]]
			reply_markup = InlineKeyboardMarkup(keyboard)
			# sent a note to all users who have access now (again)
			for user in changed_users:
				try:
					await user_context.bot.send_message(chat_id=user['user']['user_id'], text=user_context._(
						"You got a key. You can open the door now"), reply_markup=reply_markup)
				except:  # in case the user has just no chat open to this bot
					print("couldn't send addition notification to user")
			await user_context.msg.reply_text(user_context._('Key lend to {0} {1}').format(
				user_context.new_contact['first_name'], user_context.new_contact['last_name']))
		else:
			await user_context.msg.reply_text(user_context._("Something went wrong"))
		user_context.new_contact = None
		await self.menu_main(update, context, query)

	async def delete_follower_callback(self, update, context, query):
		'''deletes a user'''
		user_context = UserContext.get_user_context(update, context, query)
		delete_user = self.access_manager.user_info_by_id(query.data)
		if delete_user and user_context.user:
			changed_users = self.access_manager.delete_user_by_id(
				self.access_manager.user_id(user_context.user), query.data)
			for user in changed_users:  # sent a note to all users who have lost access now
				try:
					await context.bot.send_message(chat_id=user['user']['user_id'], text=user_context._(
						"Your key was revoked. You can not open the door anymore"))
				except:  # in case the user has just no chat open to this bot
					print("couldn't send deletion notification to user")
			await user_context.msg.reply_text(user_context._('Key brought back from {0} {1}').format(
				delete_user['first_name'], delete_user['last_name']))
		else:
			await user_context.msg.reply_text(user_context._("Something went wrong"))
		await self.menu_main(update, context, query)

	async def delete_sponsor_callback(self, update, context, query):
		'''deletes a sponsor'''
		user_context = UserContext.get_user_context(update, context, query)
		delete_user = self.access_manager.user_info_by_id(query.data)
		if delete_user and user_context.user:
			changed_users = self.access_manager.delete_user_by_id(
				query.data, self.access_manager.user_id(user_context.user))
			for user in changed_users:  # sent a note to all users who have lost access now
				try:
					await context.bot.send_message(chat_id=user['user']['user_id'], text=user_context._(
						"Your key was revoked. You can not open the door anymore"))
				except:  # in case the user has just no chat open to this bot
					print("couldn't send deletion notification to user")
			await user_context.msg.reply_text(user_context._('Key returned to {0} {1}').format(
				delete_user['first_name'], delete_user['last_name']))
		else:
			await user_context.msg.reply_text(user_context._("Something went wrong"))
		await self.menu_main(update, context, query)

	def delete_follower_by_list_item(self, update, context, query):
		'''deletes a user'''
		self.delete_follower(
			update, context, self.access_manager.user_info_by_id(query.data))

	def delete_sponsor_by_list_item(self, update, context, query):
		'''deletes a sponsor'''
		self.delete_sponsor(
			update, context, self.access_manager.user_info_by_id(query.data))

	async def list_follower_callback(self, update, context, query):
		'''creates a dynamic list of followers to select one for deletion
		'''
		user_context = UserContext.get_user_context(update, context, query)
		user_context.last_follower_pos = self.fill_list(
			query.data, self.access_manager.get_follower_list, self.delete_follower_by_list_item, self.list_follower_callback, user_context)
		user_context.add_keyboard_item('🔑'+user_context._('Key Management'), "menu",
									   self.menu_key_management, True)
		reply_markup = user_context.compile_keyboard()
		await user_context.msg.reply_text(user_context._('Choose the Key to get back'),
									reply_markup=reply_markup)

	async def list_sponsor_callback(self, update, context, query):
		'''creates a dynamic list of sponsors to select one for deletion
		'''
		user_context = UserContext.get_user_context(update, context, query)
		user_context.last_follower_pos = self.fill_list(
			query.data, self.access_manager.get_sponsor_list, self.delete_sponsor_by_list_item, self.list_sponsor_callback, user_context)
		user_context.add_keyboard_item('🔑'+user_context._('Key Management'), "menu",
									   self.menu_key_management, True)
		reply_markup = user_context.compile_keyboard()
		await user_context.msg.reply_text(user_context._('Choose the Key to get back'),
									reply_markup=reply_markup)

	def fill_list(self, last_pos, get_list, item_callback, list_callback, user_context):
		''' generic function to handle the different pages of a list to go through the list and
		select a item out of it


		Args:
				last_pos (:obj:`int`): position inside the list from where the display shall be made from. Start from 0 if pos in <0
				get_list (:obj:`function`) : callback function which provides the list to display
				item_callback (:obj:`function`) : function to be called when a item is selected
				get_list (:obj:`function`) : function to be called when nex/previous page is selected
				user_context (:obj:`obj`): User context object

		'''

		user_context.clear_keyboard()
		last_pos = int(last_pos)
		if last_pos < 0:  # a dirty trick, as we can't start all lists with the same starting index 0, as that crashes in the virtual keyboard generation, when all keyboard buttons would have the same index...
			last_pos = 0
		items_per_page = 5
		item_list = get_list(user_context.user)
		list_len = len(item_list)
		# calculate view
		for i in range(items_per_page):
			if (i+last_pos) < list_len:
				user_context.add_keyboard_item(item_list[i+last_pos]["text"], item_list[i+last_pos]["user_id"],
											   item_callback, True)
		if last_pos > 0:
			new_pos = last_pos-items_per_page
			if new_pos < 0:
				new_pos = 0
			user_context.add_keyboard_item('<', str(new_pos),
										   list_callback, True)
		else:
			user_context.add_keyboard_item('-', '0',
										   list_callback, True)
		if last_pos+items_per_page < list_len:
			user_context.add_keyboard_item('>', str(last_pos+items_per_page),
										   list_callback, False)
		else:
			user_context.add_keyboard_item('-', str(last_pos),
										   list_callback, False)

	async def menu_key_management(self, update, context, query):
		''' provides the menu for the key management
		'''
		user_context = UserContext.get_user_context(update, context, query)
		user_context.clear_keyboard()
		user_context.add_keyboard_item('👤➡👥 '+user_context._("Lend this Key"), "goto_lend",
									   self.lend_key_callback, True)
		user_context.add_keyboard_item('👤⬅👥 '+user_context._("Get lend Keys back"), "-1",  # the minus -1 is to make the index unique
									   self.list_follower_callback, True)
		user_context.add_keyboard_item('⬅👤 '+user_context._("Return borrowed Keys"), "-2",  # the minus -2 is to make the index unique
									   self.list_sponsor_callback, True)
		user_context.add_keyboard_item('🕮'+user_context._("About this Program"), "help",
									   self.menu_help, True)
		user_context.add_keyboard_item('🚪'+self.myself().first_name, "goto_main",
									   self.menu_main, True)
		reply_markup = user_context.compile_keyboard()
		await user_context.msg.reply_text(
			'🔑'+user_context._('Key Management'), reply_markup=reply_markup)

	async def lend_key_callback(self, update, context, query):
		'''gives some help text how to lend a key'''
		user_context = UserContext.get_user_context(update, context, query)
		await user_context.msg.reply_text(user_context._(
			'To lend a key\n- Go to your telegram contacts\n- select the contact to lend to\n- select his context menu\n- choose "share to"\n- share the contact to this door bot\n- follow the instructions to finish'))
		await self.menu_key_management(update, context, query)

	async def menu_main(self, update, context, query):
		''' provides the main menu
		'''
		user_context = UserContext.get_user_context(update, context, query)
		user_context.clear_keyboard()
		# known user?
		if self.access_manager.user_is_active(user_context.user) != None:
			user= await self.myself()
			text_info = '🚪'+ user.first_name
			user_context.add_keyboard_item(user_context._("New Pin"), "dummy",
										   self.menu_new_pin, True)
			user_context.add_keyboard_item('🔑'+user_context._("Key Management"), "menu",
										   self.menu_key_management, True)
		else:
			text_info = user_context._('Unknown User! ({0})').format(
				self.access_manager.user_id(user_context.user))
			user_context.add_keyboard_item('🕮'+user_context._("About this Program"), "help",
										   self.menu_help, True)
		reply_markup = user_context.compile_keyboard()
		await user_context.msg.reply_text(text_info, reply_markup=reply_markup)

	def add_follower(self, update, context, new_user):
		'''verifies, if a shared contact shall be added as new follower
		'''
		user_context = UserContext.get_user_context(update, context, None)
		user_context.clear_keyboard()
		user_context.add_keyboard_item('👤➡👥 '+user_context._("Lend Key"), "add",
									   self.add_follower_callback, True)
		user_context.add_keyboard_item('🚪'+self.myself().first_name, "goto_main",
									   self.menu_main, True)
		reply_markup = user_context.compile_keyboard()
		update.message.reply_text(
			user_context._('Ok to lend the Key to {0} {1}?').format(new_user['first_name'], new_user['last_name']), reply_markup=reply_markup)

	async def delete_follower(self, update, context, user):
		'''verifies, if a follower shall be removed
		'''
		user_context = UserContext.get_user_context(update, context, None)
		user_context.clear_keyboard()
		user_context.add_keyboard_item(user_context._("Bring Back"), self.access_manager.user_id(user),
									   self.delete_follower_callback, True)
		user_context.add_keyboard_item('🚪'+self.myself().first_name, "goto_main",
									   self.menu_main, True)
		reply_markup = user_context.compile_keyboard()
		if update.message:
			msg = update.message
		else:
			msg = update.effective_message
		await msg.reply_text(
			user_context._('Ok to bring back the key from {0} {1}?').format(user['first_name'], user['last_name']), reply_markup=reply_markup)

	async def delete_sponsor(self, update, context, user):
		'''verifies, if a sponsor shall be removed
		'''
		user_context = UserContext.get_user_context(update, context, None)
		user_context.clear_keyboard()
		user_context.add_keyboard_item(user_context._("return"), self.access_manager.user_id(user),
									   self.delete_sponsor_callback, True)
		user_context.add_keyboard_item('🚪'+self.myself().first_name, "goto_main",
									   self.menu_main, True)
		reply_markup = user_context.compile_keyboard()
		if update.message:
			msg = update.message
		else:
			msg = update.effective_message
		await msg.reply_text(
			user_context._('Ok to return the key to {0} {1}?').format(user['first_name'], user['last_name']), reply_markup=reply_markup)

	async def share_contact(self, update, context):
		user_context = UserContext.get_user_context(update, context, None)
		"""Checks, if a shared contact already exists"""
		user_context.new_contact = User(update.message.contact.first_name, update.message.contact.last_name,
										update.message.contact.user_id, None)  # contacts don't have language codes
		user_info = self.access_manager.user_is_active(
			user_context.new_contact)
		if user_info != None:
			if self.access_manager.user_is_follower(user_context.user, user_context.new_contact):
				self.delete_follower(update, context, user_info)
				return
		if self.access_manager.user_can_lend(user_context.user):
			self.add_follower(update, context, user_context.new_contact)
		else:
			await user_context.msg.reply_text(	user_context._(
				'You can not lend your key further'))

	async def button(self, update, context):
		''' generic function which is called when the user presses any button on the virtual keyboard
		'''

		user_context = UserContext.get_user_context(update, context, None)
		query = update.callback_query
		# CallbackQueries need to be answered, even if no notification to the user is needed
		# Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
		await query.answer()
		if query.data == 'main':
			# just in case a new user got his initial notification
			await self.menu_main(update, context, query)
		else:
			asyncio.run(user_context.execute_keyboard_callback(update, context, query))
		#query.edit_message_text(text="Selected option: {}".format(query.data))

	async def echo(self, update, context):
		"""Echo the user message."""
		user_context = UserContext.get_user_context(update, context, None)
		await user_context.msg.reply_text(
			user_context._("You wrote:")+update.message.text)
		print(update.message.text)
		await self.menu_main(update, context, None)

	def error(self, update, context):
		"""Log Errors caused by Updates."""
		logger.warning('Update "%s" caused error "%s"', update, context.error)

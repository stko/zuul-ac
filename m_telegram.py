#!/usr/bin/env python
# -*- coding: utf-8 -*-


from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import qrcode
import string
import secrets
import zuullogger
from io import BytesIO

import translate

_ = translate.gettext
logger=zuullogger.getLogger(__name__)




class ZuulMessengerPlugin:
	'''
	implements the connection to the telegram messenger infrastructure
	'''

	def __init__(self, messenger_token):

		"""Start the bot."""
		# Create the Updater and pass it your bot's token.
		# Make sure to set use_context=True to use the new context based callbacks
		# Post version 12 this will no longer be necessary
		updater = Updater(messenger_token, use_context=True)

		# Get the dispatcher to register handlers
		dp = updater.dispatcher

		# on different commands - answer in Telegram
		dp.add_handler(CommandHandler("start", self.start))
		dp.add_handler(CommandHandler("help", self.help))

		dp.add_handler(MessageHandler(Filters.contact, self.contact))

		# on noncommand i.e message - echo the message on Telegram
		dp.add_handler(MessageHandler(Filters.text, self.echo))

		# log all errors
		dp.add_error_handler(self.error)

		# Start the Bot
		updater.start_polling()

		# Run the bot until you press Ctrl-C or the process receives SIGINT,
		# SIGTERM or SIGABRT. This should be used most of the time, since
		# start_polling() is non-blocking and will stop the bot gracefully.
		updater.idle()


	def generateSecureRandomString(self, stringLength=10):
		"""Generate a secure random string of letters, digits and special characters """
		password_characters = string.ascii_letters + string.digits + string.punctuation
		return ''.join(secrets.choice(password_characters) for i in range(stringLength))


	def send_image(self,update):


		qr = qrcode.QRCode(
			version=1,
			error_correction=qrcode.constants.ERROR_CORRECT_L,
			box_size=10,
			border=4,
		)
		qr.add_data(self.generateSecureRandomString())
		qr.make(fit=True)

		img = qr.make_image(fill_color="black", back_color="white")

		bio = BytesIO()
		bio.name = 'image.jpeg'
		img.save(bio, 'PNG')
		bio.seek(0)
		

		update.message.reply_text(_('Dieser Code ist 60 Sekunden gültig - Halte ihn einfach vor die Kamera, um die Tür zu öffnen'))
		#update.message.reply_photo( photo= open('qr-code.png', 'rb'))
		update.message.reply_photo( photo=bio)
		update.message.reply_text(_('Wenn Du einen neuen Code brauchst, schreib hier einfach irgend etwas'))


	# Define a few command handlers. These usually take the two arguments update and
	# context. Error handlers also receive the raised TelegramError object in error.
	def start(self, update, context):
		"""Send a message when the command /start is issued."""
		update.message.reply_text(_('Hi!'))
		self.send_image(update)


	def help(self, update, context):
		"""Send a message when the command /help is issued."""
		update.message.reply_text(_('Help!'))

	def contact(self, update, context):
		"""Send a message when the command /help is issued."""
		print("contact",repr(update.message.contact.user_id))



	def echo(self, update, context):
		"""Echo the user message."""
		update.message.reply_text(_("Du schriebst:")+update.message.text)
		print(update.message.text)
		self.send_image(update)


	def error(self, update, context):
		"""Log Errors caused by Updates."""
		logger.warning('Update "%s" caused error "%s"', update, context.error)




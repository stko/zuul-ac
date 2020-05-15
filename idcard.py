#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ecdsa import SigningKey, VerifyingKey, BadSignatureError
from base64 import b64encode, b64decode
import hashlib
import datetime
from storage import Storage


def hash(my_bytes, length=10):
	''' hashes the bytes as string and returns the first chars of it
	'''

	return hashlib.sha1(my_bytes).hexdigest()[:length]


def int2base64(number):
	''' transforms a integer into a base64 string
	'''

	# Here's where the magic happens
	number_bytes = number.to_bytes(
		(number.bit_length() + 7) // 8, byteorder="big")
	encoded = b64encode(number_bytes)
	# Don't let yourself tricked by the variable and method names resemblance
	return encoded.decode()


def base642int(encoded):
	''' transforms a base64 string into a integer
	'''

	# Now, getting the number back
	decoded = b64decode(encoded)
	return int.from_bytes(decoded, byteorder="big")


def load_keys(store, name):
	''' loads key data from store identified by name (=certificate owner name string hash)

			Args:
			message (:obj:`bytes`): data to sign
			store (:obj:`obj`): storage handler
			name (:obj:`string`):certificate owner name string hash

			Return:
			wallet (:obj:`dict`): dict of all known key pairs
			key (:obj:`obj`): own key pair
	'''

	# Create a NIST192p keypair
	own_key = {}
	id_hash = hash(name.encode())
	wallet = store.read_config_value('wallet')
	if not wallet:
		wallet = {}
	if not id_hash in wallet:  # do we not have our own key pair generated yet? Do it now
		sk = SigningKey.generate()
		own_key['private'] = b64encode(sk.to_der()).decode('ascii')
		vk = sk.verifying_key
		own_key['public'] = b64encode(vk.to_der()).decode('ascii')
		own_key['name'] = name
		own_key['id'] = id_hash
		wallet[id_hash] = own_key
		store.write_config_value('wallet', wallet)
	else:
		own_key = wallet[id_hash]
	return wallet, own_key


def sign_bytes(message, store, name):
	''''sign a message (using SHA-1)

			Args:
			message (:obj:`bytes`): data to sign
			store (:obj:`obj`): storage handler
			name (:obj:`string`):certificate owner name string hash

			Return:
			signature (:obj:`string`): string representation of signature
	'''

	wallet, own_key = load_keys(store, name)
	sk = SigningKey.from_der(b64decode(own_key['private']))
	sig = sk.sign(message)
	signature = b64encode(sig).decode('ascii')
	return signature


def verify_sign(message, signature, key):
	''''Load the verifying key, message, and signature and verify the signature (assume SHA-1 hash)

			Args:
					message (:obj:`bytes`):  signed data
					signature (:obj:`string`): string representation of signature
					key (:obj:`obj`):certificate owner name string hash

			Return:
					signature (:obj:`string`): string representation of signature
	'''

	# Load the verifying key, message, and signature and verify the signature (assume SHA-1 hash):

	vk = VerifyingKey.from_der(b64decode(key['public']))
	sig = b64decode(signature)
	try:
		vk.verify(sig, message)
		print("good signature")
		return True
	except BadSignatureError:
		print("BAD SIGNATURE")
	return False


def time_base64():
	''' returns Unix timestamp as base64 string
	'''
	return int2base64(int(datetime.datetime.utcnow().timestamp()))


def unix_time():
	''' returns Unix timestamp as integer
	'''
	return int(datetime.datetime.utcnow().timestamp())


def verify_message(msg, modreq):
	''' verify received content. msg is a list containing

	Args:
			msg[0] (:obj:`str`): 10 char hex SHA1 hash of id of requestor
			msg[1] (:obj:`str`): 10 char hex SHA1 hash of id of receiver
			msg[2] (:obj:`str`): 10 char hex SHA1 hash of id of signed authority (= also lookup index for public key )
			msg[3] (:obj:`str`): The integer Unix UTC seconds time stamp base63 coded as shown in https://stackoverflow.com/a/55354665
			msg[4] (:obj:`str`): base64 encoded signature of msg[0] + ':'+msg[1]+':'+[2]+':'+[3]
			msg[5] (:obj:`str`): to be discussed: optional identifier of reason (e.g. packet delivery confirmation ??)

			Return:
			result (:obj:`bool`): True if signature is valid and fits to message
	'''

	if len(msg) < 5:
		print('illegal token format')
		return False
	receiver = modreq.messenger.messenger.myself()['username']
	if msg[1] != hash(receiver.encode()):  # wrong receipient :-)
		return False
	authority_id = msg[2]
	wallet = modreq.store.read_config_value('wallet')
	if not wallet or not authority_id in wallet:  # unknown authority
		return False
	this_key = wallet[authority_id]
	timestamp = base642int(msg[3])
	try:
		timeout = this_key['timeout']
	except:
		timeout = 60  # default token lifetime 60 secs
	if unix_time()-timeout > timestamp:  # token too old
		return False
	message = ":".join(msg[:4])
	signature = msg[4]
	return verify_sign(message.encode(), signature, this_key)


def get_id_card_string(store, requestor, receiver, botname):
	'''
	Args:
			store (:obj:`obj`): storage handler
			receiver (:obj:`string`) :name of receiving bot
			botname (:obj:`string`): name of the own bot

			Return:
			wallet (:obj:`dict`): dict of all known key pairs
			key (:obj:`obj`): own key pair
			message (:obj:`bytes`):  signed data
			signature (:obj:`string`): string representation of signature
			key (:obj:`obj`):certificate owner name string hash

	Return:
			message (:obj:`string`): ':' seperated string of
					msg[0] (:obj:`str`): 10 char hex SHA1 hash of id of requestor
					msg[1] (:obj:`str`): 10 char hex SHA1 hash of id of receiver
					msg[2] (:obj:`str`): 10 char hex SHA1 hash of id of signed authority (= also lookup index for public key )
					msg[3] (:obj:`str`): The integer Unix UTC seconds time stamp base63 coded as shown in https://stackoverflow.com/a/55354665
					msg[4] (:obj:`str`): base64 encoded signature of msg[0] + ':'+msg[1]+':'+[2]+':'+[3]
			'''
	message = ":".join([hash(requestor.encode()), hash(
		receiver.encode()), hash(botname.encode()), time_base64()])
	signature = sign_bytes(message.encode(), store, botname)
	return ":".join([message, signature])


if __name__ == '__main__':
	#key = create_keys()
	message = "message".encode()
	store = Storage(None)
	signature = sign_bytes(message, store, "Meier")
	wallet, key = load_keys(store, "Meier")
	verify_sign(message, signature, key)
	print(hash("my message".encode("UTF-8")))
	number = int(datetime.datetime.utcnow().timestamp())
	number_string = int2base64(number)
	print(number_string)
	number2 = base642int(number_string)
	print(number == number2)

# >>> hash = hashlib.sha1("my message".encode("UTF-8")).hexdigest()
# >>> hash
# '104ab42f1193c336aa2cf08a2c946d5c6fd0fcdb'
# >>> hash[:10]
# '104ab42f11'


#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ecdsa import SigningKey, VerifyingKey, BadSignatureError
from base64 import b64encode, b64decode
import hashlib
import datetime
from storage import Storage

def hash(my_bytes, length=10):
	return hashlib.sha1(my_bytes).hexdigest()[:length]


def int2base64(number):
	# Here's where the magic happens
	number_bytes = number.to_bytes(
		(number.bit_length() + 7) // 8, byteorder="big")
	encoded = b64encode(number_bytes)
	# Don't let yourself tricked by the variable and method names resemblance
	return encoded.decode()


def base642int(encoded):
	# Now, getting the number back
	decoded = b64decode(encoded)
	return int.from_bytes(decoded, byteorder="big")

def load_keys(store, name):
	# Create a NIST192p keypair
	own_key = {}
	id_hash = hash(name.encode())
	wallet = store.read_config_value('wallet')
	if not wallet:
		wallet = {}
	if not id_hash in wallet:  # no keys generated yet? Do it now
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
	print(repr(wallet[id_hash]))
	return wallet, own_key

def sign_bytes(message, store, name):
	# sign a message (using SHA-1)
	wallet, own_key = load_keys(store, name)
	sk = SigningKey.from_der(b64decode(own_key['private']))
	sig = sk.sign(message)
	signature = b64encode(sig).decode('ascii')
	print(signature)
	return signature


def verify_sign(message, signature, key):
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
	return int2base64(int(datetime.datetime.utcnow().timestamp()))

def unix_time():
	return int(datetime.datetime.utcnow().timestamp())

def verify_message(msg,modreq):
	''' verify received content. msg is a list containing

	Args:
			msg[0] (:obj:`str`): 10 char hex SHA1 hash of id of requestor
			msg[1] (:obj:`str`): 10 char hex SHA1 hash of id of receiver
			msg[2] (:obj:`str`): 10 char hex SHA1 hash of id of signed authority (= also lookup index for public key )
			msg[3] (:obj:`str`): The integer Unix UTC seconds time stamp base63 coded as shown in https://stackoverflow.com/a/55354665
			msg[4] (:obj:`str`): base64 encoded signature of msg[0] + ':'+msg[1]+':'+[2]+':'+[3]
			msg[5] (:obj:`str`): to be discussed: optional identifier of reason (e.g. packet delivery confirmation ??)


	'''
	if len(msg)<5:
		print('illegal token format')
		return False
	receiver=modreq.messenger.messenger.myself()['username']
	if msg[1]!=hash(receiver.encode()): # wrong receipient :-)
		return False
	authority_id=msg[2]
	wallet = modreq.store.read_config_value('wallet')
	if not wallet or not authority_id in wallet: # unknown authority
		return False
	this_key=wallet[authority_id]
	timestamp=base642int(msg[3])
	try:
		timeout=this_key['timeout']
	except:
		timeout=60 #default token lifetime 60 secs
	if unix_time()-timeout>timestamp: # token too old
		return False
	message=":".join(msg[:4])
	signature=msg[4]
	return 	verify_sign(message.encode(), signature,this_key)


def get_id_card_string(store, requestor,receiver, botname):
	message=":".join([hash(requestor.encode()),hash(receiver.encode()),hash(botname.encode()),time_base64()])
	signature = sign_bytes(message.encode(),store, botname)
	return ":".join([message,signature])

if __name__ == '__main__':
	#key = create_keys()
	message = "message".encode()
	store=Storage(None)
	signature = sign_bytes(message,store, "Meier")
	wallet, key = load_keys(store, "Meier")
	verify_sign(message, signature,key)
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

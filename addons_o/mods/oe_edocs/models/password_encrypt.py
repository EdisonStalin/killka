# -*- coding: utf-8 -*-

from cryptography.fernet import Fernet


class AESCipher(object):

    def __init__(self):
        key = bytes('UGY0oTLns86hx0nrtJbZa0BYe7rQK9y7Bpe4vpqGpL0=', 'utf-8')
        self.rkey = Fernet(key)

    def encrypt(self, raw):
        raw = bytes(raw, 'utf-8')
        token = self.rkey.encrypt(raw)
        token = str(token, 'utf-8')
        return token

    def decrypt(self, token):
        token = bytes(token, 'utf-8')
        decoded = self.rkey.decrypt(token)
        return decoded

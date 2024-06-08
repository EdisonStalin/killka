#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class SriService(object):
    
    __AMBIENTE_PRUEBA = '1'
    __AMBIENTE_PROD = '2'
    __ACTIVE_ENV = False
    
    __WS_TEST_RECEIV = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
    __WS_TEST_AUTH = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'
    __WS_RECEIV = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl'
    __WS_AUTH = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl'
    
    __WS_TESTING = (__WS_TEST_RECEIV, __WS_TEST_AUTH)
    __WS_PROD = (__WS_RECEIV, __WS_AUTH)

    
    _WSDL = {
        __AMBIENTE_PRUEBA: __WS_TESTING,
        __AMBIENTE_PROD: __WS_PROD
    }

    @classmethod
    def set_active_env(self, env_service):
        if env_service == self.__AMBIENTE_PRUEBA:
            self.__ACTIVE_ENV = self.__AMBIENTE_PRUEBA
        else:
            self.__ACTIVE_ENV = self.__AMBIENTE_PROD
        self.__WS_ACTIVE = self._WSDL[self.__ACTIVE_ENV]

    @classmethod
    def get_active_env(self):
        return self.__ACTIVE_ENV

    @classmethod
    def get_env_test(self):
        return self.__AMBIENTE_PRUEBA

    @classmethod
    def get_env_prod(self):
        return self.__AMBIENTE_PROD

    @classmethod
    def get_ws_test(self):
        return self.__WS_TEST_RECEIV, self.__WS_TEST_AUTH

    @classmethod
    def get_ws_prod(self):
        return self.__WS_RECEIV, self.__WS_AUTH

    @classmethod
    def get_active_ws(self):
        res = self.__WS_ACTIVE
        return res

# Copyright (C) 2015  Custodia Project Contributors - see LICENSE file

import os

from cryptography.hazmat.primitives import constant_time

from custodia import log
from custodia.httpd.server import HTTPError


class HTTPAuthenticator(log.CustodiaPlugin):

    def handle(self, request):
        raise HTTPError(403)


class SimpleCredsAuth(HTTPAuthenticator):

    def __init__(self, config=None):
        super(SimpleCredsAuth, self).__init__(config)
        self._uid = 0
        self._gid = 0
        if 'uid' in self.config:
            self._uid = int(self.config['uid'])
        if 'gid' in self.config:
            self._gid = int(self.config['gid'])

    def handle(self, request):
        creds = request.get('creds')
        if creds is None:
            self.logger.debug('SCA: Missing "creds" from request')
            return False
        uid = int(creds['gid'])
        gid = int(creds['uid'])
        if self._gid == gid or self._uid == uid:
            self.audit_svc_access(log.AUDIT_SVC_AUTH_PASS,
                                  request['client_id'],
                                  "%d, %d" % (uid, gid))
            return True
        else:
            self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                  request['client_id'],
                                  "%d, %d" % (uid, gid))
            return False


class SimpleHeaderAuth(HTTPAuthenticator):

    def __init__(self, config=None):
        super(SimpleHeaderAuth, self).__init__(config)
        self.name = 'REMOTE_USER'
        self.value = None
        if 'header' in self.config:
            self.name = self.config['header']
        if 'value' in self.config:
            self.value = self.config['value']

    def handle(self, request):
        if self.name not in request['headers']:
            self.logger.debug('SHA: No "headers" in request')
            return None
        value = request['headers'][self.name]
        if self.value is None:
            # Any value is accepted
            pass
        elif isinstance(self.value, str):
            if value != self.value:
                self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                      request['client_id'], value)
                return False
        elif isinstance(self.value, list):
            if value not in self.value:
                self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                      request['client_id'], value)
                return False
        else:
            self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                  request['client_id'], value)
            return False

        self.audit_svc_access(log.AUDIT_SVC_AUTH_PASS,
                              request['client_id'], value)
        request['remote_user'] = value
        return True


class SimpleAuthKeys(HTTPAuthenticator):

    def __init__(self, config=None):
        super(SimpleAuthKeys, self).__init__(config)
        self.id_header = self.config.get('header', 'CUSTODIA_AUTH_ID')
        self.key_header = self.config.get('header', 'CUSTODIA_AUTH_KEY')
        self.store_name = self.config['store']
        self.store = None
        self.namespace = self.config.get('store_namespace', 'custodiaSAK')

    def _db_key(self, name):
        return os.path.join(self.namespace, name)

    def handle(self, request):
        name = request['headers'].get(self.id_header, None)
        key = request['headers'].get(self.key_header, None)
        if name is None and key is None:
            self.logger.debug('Ignoring request no relevant headers provided')
            return None

        validated = False
        try:
            val = self.store.get(self._db_key(name))
            if val is None:
                raise Exception("No such ID")
            if constant_time.bytes_eq(val.encode('utf-8'),
                                      key.encode('utf-8')):
                validated = True
        except Exception:  # pylint: disable=broad-except
            self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                                  request['client_id'], name)
            return False

        if validated:
            self.audit_svc_access(log.AUDIT_SVC_AUTH_PASS,
                                  request['client_id'], name)
            request['remote_user'] = name
            return True

        self.audit_svc_access(log.AUDIT_SVC_AUTH_FAIL,
                              request['client_id'], name)
        return False

import base64
import os
import random
import string
import time
import re
import hashlib

#M2Crypto is not available on the Windows version of splunk
if os.name != 'nt':
    from M2Crypto import RSA

import splunk.rest as rest
import splunk.entity as en
import dbx2.utils as utils
import urlparse

from dbx2.dbx_logger import logger

AUTH_TOKENS_ENDPOINT = '/services/admin/auth-tokens'
AUTH_CERT_ENDPOINT = '/services/admin/certificates'
SPLUNK_HOME = os.environ['SPLUNK_HOME']
PRIV_KEY_PATH = os.path.join(SPLUNK_HOME, 'etc', 'auth', 'distServerKeys', 'private.pem')

USERNAME   = "username"
USERID      = "userid"
SIGNATURE   = "sig"
NONCE       = "nonce"
TS          = "ts"
PEERNAME    = "peername"
CERTIFICATE = "certificate"

def call_peer(remote_host, remote_user, local_host, local_user, ts, nonce, signature):
    #DBX-2442
    if not utils.validateHostName(remote_host):
       logger.debug("invalid remote_host")
       return None
    if not utils.validateHostName(local_host):
       logger.debug("invalid local_host")
       return None
    
    if not utils.validateUserName(remote_user):
       logger.debug("invalid remote_user")
       return None
 
    if not utils.validateUserName(local_user):
       logger.debug("invalid local_user")
       return None

    ''' make remote REST call to retreive foreign sessionKey '''
    postargs = {
        'name': '_create',
        USERID: local_user,
        PEERNAME: local_host,
        USERNAME: remote_user,
        TS: ts,
        NONCE: nonce,
        SIGNATURE: signature
    }
    
    logger.debug('call peer: remote_host=%s postargs=%s' % (remote_host, postargs))

    resp, cont = rest.simpleRequest(remote_host + AUTH_TOKENS_ENDPOINT, postargs=postargs)

    if resp.status not in [200, 201]:
        logger.error('unable to get session key from remote peer %s' % remote_host)
        return None
    try:
        atomEntry = rest.format.parseFeedDocument(cont)
        logger.debug('response from peer:\n%s' % atomEntry.toPrimitive())
        ret = atomEntry.toPrimitive()[remote_user][remote_user]
        return ret
    except Exception, ex:
        logger.error('unable to parse response from remote peer %s' % remote_host)
        logger.exception(ex)
        return None

def gen_nonce(local_user):
    ''' generate a nonce '''
    asc_time = time.asctime(time.localtime())
    rand_num = gen_rand()
    m = hashlib.sha256
    return m(''.join([asc_time, local_user, rand_num])).hexdigest()

def gen_rand(size=256, chars=string.ascii_uppercase + string.digits):
    '''
    http://stackoverflow.com/questions/2257441/random-string-generation-with-upper-case-letters-and-digits-in-python/23728630#23728630

    Using random.SystemRandom() instead of just random uses /dev/urandom on *nix machines and CryptGenRandom()
    in Windows. These are cryptographically secure PRNGs.
    '''
    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))

def gen_sig(rsa, local_user, remote_user, nonce, ts):
    ''' generate a signature '''
    plain_text = ''.join([local_user, remote_user, nonce, ts])
    return base64.b64encode(rsa.private_encrypt(plain_text, RSA.pkcs1_padding))

def get_private_key(key_path=None):
    ''' load local instance private key and return rsa instance '''
    try:
        if (key_path is None):
            key_path = PRIV_KEY_PATH
        logger.debug("Loading private key from: %s" % os.path.expandvars(key_path))
        return RSA.load_key(key_path)
    except Exception, ex:
        logger.error('unable to load private key %s' % key_path)
        logger.debug(ex)
        return None

def get_remote_token(remote_host, remote_user, local_host, local_user, key_path=None):
    nonce = gen_nonce(local_user)
    ts = str(time.mktime(time.gmtime()))[:-2]
    rsa = get_private_key(key_path)
    if rsa is None:
        return rsa
    signature = gen_sig(rsa, local_user, remote_user, nonce, ts)

    return call_peer(remote_host, remote_user, local_host, local_user, ts, nonce, signature)

def get_local_host(host_path, sessionKey):
    return en.getEntity('/server/info', 'server-info', sessionKey=sessionKey, hostPath=host_path).properties['serverName']

def get_token(url, localSessionKey):
    parsed_url = urlparse.urlparse(url)
    remote_host = parsed_url.scheme + "://" + parsed_url.netloc
    #DBX-2442
    if not utils.validateHostName(remote_host):
       logger.debug("invalid remote_host")
       return None

    ''' for local calls we should user the current session '''
    local_settings = en.getEntity('/server/settings', 'settings', sessionKey=localSessionKey)
    local_url =  local_settings["host"] + ":" + local_settings["mgmtHostPort"]
    if (parsed_url.netloc.lower() == local_url.lower()):
       return localSessionKey
    local_host = get_local_host(None, localSessionKey)
    remote_user = local_user = "splunk-system-user"
    remoteKey = get_remote_token(remote_host, remote_user, local_host, local_user)
    logger.debug("getRemoteKey: got remote token for: %s %s %s %s %s" % (remote_host, remote_user, local_host, local_user, remoteKey))
    return remoteKey

def set_certificate(remote_host, local_host, local_cert, sessionKey):
    #DBX-2442
    if not utils.validateHostName(remote_host):
       raise Exception("invalid remote_host")
    if not utils.validateHostName(local_host):
       raise Exception("invalid local_host")

    postargs = {
        PEERNAME: local_host,
        CERTIFICATE: local_cert
    }

    logger.debug('set_certificate: remote_host=%s postargs=%s' % (remote_host, postargs))

    resp, cont = rest.simpleRequest(remote_host + AUTH_CERT_ENDPOINT + '/' + local_host, sessionKey=sessionKey, postargs=postargs)

    if resp.status not in [200, 201]:
        logger.error('unable to post certificate to remote peer %s %d' % (remote_host, resp.status))
        raise Exception('posting certificate to remote peer failed')
    return

def getRemoteKey(node, sessionKey):
    parsed_url = urlparse.urlparse(node)
    url = parsed_url.scheme + "://" + parsed_url.netloc
    ''' for local calls we should user the current session '''
    local_settings = en.getEntity('/server/settings', 'settings', sessionKey=sessionKey)
    local_url = "https://" + local_settings["host"] + ":" + local_settings["mgmtHostPort"]
    if (url.lower() == local_url.lower()):
       return sessionKey
    '''TODO: change this to splunkds endpoint'''
    local_host = get_local_host(None, sessionKey)
    remote_user = local_user = "splunk-system-user"
    remoteKey = get_remote_token(url, remote_user, local_host, local_user)
    logger.debug("getRemoteKey: got remote token for: %s %s %s %s %s" % (url, remote_user, local_host, local_user, remoteKey))
    return remoteKey


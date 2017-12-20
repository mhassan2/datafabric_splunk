from functools import wraps
import os

import re
import xml.dom.minidom
import sys
import exceptions
import conf_util
import C

HOSTNAME_BLACKLIST="\n|\t|\r"
USERNAME_BLACKLIST="/| |\n|\t|\r"
from dbx_logger import logger

"""
read XML configuration passed from splunkd, an example is:

<input>
  <server_host>btsay-mbp15.local</server_host>
  <server_uri>https://127.0.0.1:8089</server_uri>
  <session_key>8f99503c517b3b105148a1c20de4093c</session_key>
  <checkpoint_dir>/Applications/Splunk/var/lib/splunk/modinputs/rpcstart</checkpoint_dir>
  <configuration>
    <stanza name="rpcstart://default">
      <param name="disabled">0</param>
      <param name="host">btsay-mbp15.local</param>
      <param name="index">main</param>
      <param name="interval">0</param>
      <param name="javahome">/Library/Java/JavaVirtualMachines/jdk1.7.0_51.jdk/Contents/Home</param>
      <param name="options">-Xmx512m -Xdebug -Xnoagent -Xrunjdwp:transport=dt_socket,server=y,suspend=n,address=5555</param>
      <param name="port">9998</param>
    </stanza>
  </configuration>
</input>

"""
def get_config(config_str):
    config = {}
    try:
        doc = xml.dom.minidom.parseString(config_str.strip())
        server_uri = doc.getElementsByTagName("server_uri")[0]
        session_key = doc.getElementsByTagName("session_key")[0]
        config["server_uri"] = server_uri.childNodes[0].nodeValue
        config["session_key"] = session_key.childNodes[0].nodeValue

        root = doc.documentElement
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data

        if not config:
            raise Exception, "Invalid configuration received from Splunk."

    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

    return config

"""
 replace_props is to replace and parameters as <a>:<b>?<c> with the values from parameters a, b, c
 example:
 x = "<a>?<b>"
 a = "w"
 b = "s"

 then x = "w?s" after replacements.
"""

def parse_tokens(line):
    return [v.strip("<").strip(">") for v in re.findall("<\w+>", line)]

def replace_tokens(line, dic):
    tokens = parse_tokens(line)
    for t in tokens:
        if dic.has_key(t) and type(dic[t]) is str:
            line = line.replace("<%s>"%t, dic[t])

    return line


def replace_props(dic):
    values = {}

    for n, v in dic.items():
        values[n] = replace_tokens(v, dic) if type(v) is str else v

    return values

'''
    replace <prop> with values then filter items in names
'''
def filter_dict(dic, names):
    d = replace_props(dic)
    return dict(filter(lambda n: n[0] in names, d.items()))

import hashlib
def hexhash(tohash):
    return hashlib.sha1(str(tohash)).hexdigest()

def inthash(tohash):
    return int(hash(str(tohash)), 16)

def quote_str(s):
    return "\"%s\"" % s.replace('"', "'")

def get_key(configs, key, default=None):
    if configs.has_key(key):
        v = configs[key]
        if v and len(str(v).strip()) > 0:
            return v

    return default

def get_boolean(configs, key, default=False):
    if configs.has_key(key):
        v = configs[key]
        if v and str(v) in ["1", "true", "True"]:
            return True

    return default

def get_boolvalue(v):
    return v and str(v).upper() in ["1", "TRUE"]

def get_positive_int(configs, name, default=None):
    value = default
    if configs.has_key(name):
        value = int(configs[name])

        if value < 0:
            value = None

    return value

def validateHostName(host, blacklist=None):
    if blacklist is None:
        blacklist = HOSTNAME_BLACKLIST
    if host is None:
        return True
    if re.search(blacklist, host):
        return False
    return True

def validateUserName(user, blacklist=None):
    if blacklist is None:
        blacklist = USERNAME_BLACKLIST
    if user is None:
        return True
    if re.search(blacklist, user):
        return False
    return True

"""
Check whether pid exists in the current process table.
UNIX only - This method cannot work on windows.
"""

"""
import errno
def pid_exists(pid):
    assert pid > 0, "PID = %s must not be zero or negative" % pid
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH)
            raise
    else:
        return True

if __name__ == "__main__":
    x = {'database': 'sakila', 'password': 'enc:26e8fchOxTfk6/DQQLS9qw==', 'jdbcUrlFormat': 'jdbc:mysql://<host>:<port>/<database>', 'port': '3306', 'disabled': '0', 'displayName': 'MySQL', 'type': 'mysql', 'testQuery': 'SELECT 1', 'eai:appName': 'splunk_app_db_connect', 'typeClass': 'com.splunk.dbx2.GenericJDBC', 'jdbcDriverClass': 'com.mysql.jdbc.Driver', 'eai:acl': {'can_list': '1', 'sharing': 'app', 'can_share_user': '0', 'can_share_app': '1', 'owner': 'nobody', 'app': 'splunk_app_db_connect', 'can_write': '1', 'can_change_perms': '1', 'removable': '1', 'modifiable': '1', 'perms': {'read': ['admin', 'dbx_user'], 'write': ['admin']}, 'can_share_global': '1'}, 'host': 'localhost', 'username': 'dbconnect', 'eai:userName': 'nobody'}
    print filter_dict(x, ["jdbcUrlFormat", "username", "password"])
"""


def get_cert_dir():
    path_to_app = os.path.join(os.environ.get('SPLUNK_HOME'), 'etc', 'apps', 'splunk_app_db_connect')
    return os.path.join(path_to_app, 'certs')

def os_specific_sys_exit(sysVal):
    # Note: please use instead of sys.exit(), as this version passes exit codes
    # according to OS type. Assumes the only valid operating systems are Windows and
    # POSIX based, and return 32-bit unsigned ints for Windows, and 8-bit for POSIX
    # (DBX-1663).
    if sysVal < 0:
        if os.name == 'nt':
            sysVal += 2**32
        else:
            sysVal += 2**8

    sys.exit(sysVal)


def trace(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        logger.debug("entering %s", func.__name__)
        result = func(*args, **kwargs)
        logger.debug("exiting %s", func.__name__)
        return result
    return func_wrapper

def _check_mandatory_fields(conf):
    mandatory_fields = [C.JDBC_URL, C.SERVICE_CLASS, C.DRIVER_CLASS]
    for cc in mandatory_fields:
        if not conf.has_key(cc):
            raise exceptions.ResourceNotFoundException('%s is a mandatory parameter for the database connection.' % cc)

def _check_ssl(conf):
    is_use_ssl = conf_util.normalizeBoolean(conf.get(C.JDBC_USE_SSL, 'false'))
    if is_use_ssl and not conf.has_key(C.JDBC_SSL_URL):
        raise Exception('The parameter %s is not set, this configuration cannot do SSL connection.' % C.JDBC_SSL_URL)
    return is_use_ssl

def _update_non_ssl_url(conf, is_use_ssl):
    if is_use_ssl:
        conf[C.JDBC_URL] = conf[C.JDBC_SSL_URL]
    return conf

def copy_dbconf(configs):
    _check_mandatory_fields(configs)
    is_use_ssl = _check_ssl(configs)
    cloned_conf = {k: str(v) for k, v in configs.items()}
    return _update_non_ssl_url(cloned_conf, is_use_ssl)

# convert dictionary into kv string for log
def dict_to_kv(dictionary):
    return ' '.join(['%s=%s' % (k, v) for k, v in sorted(dictionary.items())])

def is_supported_version(supportedVersion, installedMajor=0, installedMinor=0):
    version_dict = {}

    for item in supportedVersion.split(','):
        fields = item.split('.')
        k = fields[0].strip()
        v = '-1'

        # Only major version is provided, set the tiny version to 0 manually.
        if len(fields) == 1:
            v = '0'
            logger.info('Only major version is provided: %s', item)
        else:
            v = fields[1].strip()
            if len(fields) > 2:
                logger.info('Omit tiny version number: %s', item)

        # Skip if current major version is in version dict, and tiny version
        # is higher than existing version entry.
        if k in version_dict and int(v) >= int(version_dict[k]):
            continue

        version_dict[k] = v

    is_supported = ((str(installedMajor) in version_dict) and
                    (int(installedMinor) >= int(version_dict[str(installedMajor)])))

    return 1 if is_supported else 0

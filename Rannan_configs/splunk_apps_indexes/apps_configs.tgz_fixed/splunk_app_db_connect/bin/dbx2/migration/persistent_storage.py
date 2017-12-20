import hashlib
import os
import lxml.etree as et
from dbx2.dbx_logger import logger


SPLUNK_DB = os.environ['SPLUNK_DB']
SPLUNK_HOME = os.environ['SPLUNK_HOME']


class SplunkPersistentStorage(object):
    """
    read only support for persistent storage used by dbx1
    """
    @property
    def _get_persistent_storage_dir(self):
        if SPLUNK_DB is not None:
            return os.path.join(SPLUNK_DB, 'persistentstorage', 'dbx')

        return os.path.join(SPLUNK_HOME, 'var', 'run', 'splunk', 'persistentstorage', 'dbx')

    def __init__(self, stanza_name):
        self.stanza_name = stanza_name

        # dbx1 md5s the stanza name and use it as a hash for the persistent storage
        m = hashlib.md5(self.stanza_name).hexdigest()
        self.dir_name = os.path.join(self._get_persistent_storage_dir, m)

        file_path = os.path.join(self.dir_name, 'state.xml')
        self.data = {}

        # state.xml is in a simplifed xml form
        with open(file_path) as fd:
            root = et.fromstring(fd.read())

            for element in root:
                key = element.get('key')
                value = element.find('value')
                if key is not None and value is not None:
                    self.data[key] = value.text

    def get(self, key):
        """
        raises KeyError exception if key does not exist, otherwise it returns the value for the key
        """
        return self.data[key]

import subprocess
import os

from base64 import b64decode

from dbx2.exceptions import AttributeMissingException
from dbx2.migration import BaseMigration


SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
SPLUNK_SECRET = os.path.join(SPLUNK_HOME, "etc", "auth", "splunk.secret")


class MigrateIdentityFromDBX1(BaseMigration):
    @property
    def splunk_secret_key(self):
        if not hasattr(self, '_key'):
            try:
                with open(SPLUNK_SECRET) as fd:
                    fd.seek(33)
                    self._key = fd.read(16)
            except IOError:
                raise Exception("splunk.secret cannot be located or open")

            return self._key

        return self._key

    def setup(self, session_key=None):
        self._decrypt_password()

    def _decrypt_password(self):
        """
        decrypts the password from the source and stores it in the dst. This function relies on "openssl"
        via a subprocess to avoid pycrypto library's problems on certain operating systems.
        """
        password_base64 = self.src.content.get('password')
        if not password_base64:
            return

        # strip off "enc:"
        password_base64 = password_base64[4:].decode('UTF-8')

        # the password is stored in base64
        password_aes_encrypted = b64decode(password_base64)

        decrypt_command = 'openssl aes-128-ecb -d -K {}'.format(self.splunk_secret_key.encode('hex'))

        proc = subprocess.Popen(decrypt_command.split(), stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(password_aes_encrypted)
        if stderr:
            raise Exception("the password from the migration origin cannot be decrypted ({})".format(stderr))

        self.dst.content['password'] = stdout

    def migrate(self):
        entity = self.dst

        # since "identity" is new in dbx2, use dbname_username as the name of the identity
        try:
            identity = entity.name
        except KeyError:
            raise AttributeMissingException('username')

        entity.rename(identity)
        entity.filter_attrs('username', 'password')
        entity.rename_conf('identity')

    def validate(self):
        pass

    def teardown(self):
        pass


import splunk.entity as en

from dbx2.exceptions import ValidationFailedException
from dbx2.migration import BaseMigration


NAMESPACE = 'splunk_app_db_connect'
OWNER = 'nobody'


class MigrateConnectionFromDBX1(BaseMigration):
    """
    database.conf in dbx1 -> db_connections.conf in dbx2
    """

    DB_TYPE_MAP = {
        'mssql': 'mssql',
        'oracle': 'oracle',
        'mysql': 'mysql',
        'postgresql': 'postgres',
        'sybase': 'sybase_ase',
        'hsql': 'hsqldb',
        'db2': 'db2',
        'informix': 'informix'
    }

    def setup(self, session_key=None):
        self.connection_type = None
        self.jdbc_url_format = None

        try:
            db_type = self.src.content['type']
            self.connection_type = self.DB_TYPE_MAP[db_type]

        except KeyError:
            raise ValidationFailedException('{} is no longer supported by DB Connect 2'.format(db_type))

        self._set_jdbc_url_format(session_key)

    def _set_jdbc_url_format(self, session_key):
        entity = en.getEntity(['db_connect', 'connection_types'], self.connection_type, namespace=NAMESPACE,
                              owner=OWNER, sessionKey=session_key)

        self.jdbc_url_format = entity['jdbcUrlFormat']

    def _handle_args(self, entity):
        # Additional JDBC params are only supported for informix and mssql
        arguments = {}
        if 'arguments' not in self.src.content:
            return

        pairs = self.src.content.get('arguments').split(';')
        for pair in pairs:
            try:
                key, value = pair.split('=')
                arguments[key] = value
            except ValueError:
                raise ValidationFailedException('"Additional JDBC Parameters" not valid')

        try:
            if self.connection_type == 'informix':
                server_name = arguments.pop('informix.server')
                entity.set(informixserver=server_name)

            elif self.connection_type == 'mssql':
                # useCursors is now the default jdbcUrlFormat. we can ignore it
                arguments.pop('useCursors')
            else:
                return
        except KeyError:
            pass

        if arguments:
            arg_string = ['{}={}'.format(key, value) for key, value in arguments.iteritems()]
            entity.set(jdbcUrlFormat='{};{}'.format(self.jdbc_url_format, ';'.join(arg_string)))

    def migrate(self):
        entity = self.dst

        entity.set(connection_type=self.connection_type,
                   identity=self.src.name)

        self._handle_args(entity)

        entity.filter_attrs('jdbcUrlFormat',
                            'jdbcUrlSSLFormat',
                            'testQuery',
                            'database',
                            'identity',
                            'isolation_level',
                            'readonly',
                            'host',
                            'port',
                            'informixserver',
                            'useConnectionPool',
                            'connection_type')

    def validate(self):
        pass

    def teardown(self):
        pass

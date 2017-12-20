import re

from splunk.util import normalizeBoolean


from dbx2.exceptions import EntityCanNotBeMigrated
from dbx2.migration import BaseMigration
from dbx2.migration.persistent_storage import SplunkPersistentStorage


class MigrateInputFromDBX1(BaseMigration):
    """
    inputs.conf in dbx1 -> inputs.conf in dbx2
    """

    def setup(self, session_key=None):
        stanza_name = self.src.name
        self.storage = None

        try:
            self.storage = SplunkPersistentStorage(stanza_name)
        except IOError:
            # storage is only used for tail.rising.column
            pass

    def migrate(self):
        entity = self.dst

        name_pattern = r'dbmon-(?P<type>\w+)://(?P<database>\w+)/(?P<unique_name>\w+)'
        r = re.match(name_pattern, self.src.name)
        if not r:
            raise EntityCanNotBeMigrated('this entity, {} is not an input entity'.format(self.src.name))

        mode = r.group('type')
        database = r.group('database')
        unique_name = r.group('unique_name')

        entity.rename('mi_input://' + unique_name)

        if normalizeBoolean(self.src.content.get('output.timestamp', 'false')):
            timestamp_column = self.src.content.get('output.timestamp.column')
            if timestamp_column:
                entity.set(input_timestamp_column_name=timestamp_column)

            timestamp_format = self.src.content.get('output.timestamp.format')
            if timestamp_format:
                entity.set(input_timestamp_format=timestamp_format)

        # rising column
        if mode == 'tail':
            checkpoint = None
            column_name = self.src.content.get('tail.rising.column')
            try:
                key = "latest." + column_name

                if self.storage:
                    checkpoint = self.storage.get(key)

            except (KeyError, AttributeError) as e:
                # if, for some odd reason, tail.rising.column is not defined
                pass

            entity.set(tail_follow_only='1',
                       tail_rising_column_name=self.src.content.get('tail.rising.column'),
                       tail_rising_column_checkpoint_value=checkpoint,
                       mode='tail')
        else:
            # both dump/batch get "batch"
            mode = 'batch'

        if self.src.content.get('query') is None and self.src.content.get('table'):
            entity.set(query='SELECT * FROM {}'.format(self.src.content.get('table')))

        if self.src.content.get('sourcetype') is None:
            entity.set(sourcetype='{}:{}'.format(database, unique_name))

        if self.src.content.get('interval') is None:
            entity.set(interval='86400')  # defaults to once a day thing

        entity.set(mode=mode, connection=database)
        entity.set(ui_query_mode='advanced')
        entity.set(source='//{}/{}'.format(database, unique_name))

        entity.filter_attrs('index', 'source', 'sourcetype',
                            'description', 'mode', 'connection', 'query', 'query_timeout', 'max_rows',
                            'tail_follow_only', 'tail_rising_column_name', 'tail_rising_column_number',
                            'tail_rising_column_checkpoint_value', 'input_timestamp_column_name',
                            'input_timestamp_column_number', 'input_timestamp_format', 'output_timestamp_format',
                            'ui_query_mode', 'ui_query_catalog', 'ui_query_schema', 'ui_query_table',
                            'resource_pool', 'interval')

    def validate(self):
        pass

    def teardown(self):
        pass

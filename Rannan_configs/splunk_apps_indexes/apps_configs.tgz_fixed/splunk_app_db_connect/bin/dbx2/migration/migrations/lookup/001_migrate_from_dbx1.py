import json

from splunk.util import normalizeBoolean

from dbx2.exceptions import AttributeMissingException
from dbx2.migration import BaseMigration


class MigrateLookupFromDBX1(BaseMigration):
    """
    lookups.conf in dbx1 -> inputs.conf in dbx2
    """

    def setup(self, session_key=None):
        pass

    def migrate(self):
        entity = self.dst

        entity.rename(self.src.name)

        fields = None
        lookup_SQL = None

        try:
            fields = self.src.content.get('fields').split(',')

            advanced = normalizeBoolean(self.src.content.get('advanced', '0'))
            if not advanced:
                # If dbx1 mode is advanced=0 , then set lookupSQL = SELECT * FROM <table>
                lookup_SQL = 'SELECT * FROM {}'.format(self.src.content['table'])

                # assume that the first field is the input field
                input_fields = fields[:1]
                output_fields = fields[1:]

            else:
                lookup_SQL = self.src.content.get('query')
                input_fields = self.src.content.get('input_fields').split(',')
                output_fields = [field for field in fields if field not in input_fields]

        except:
            raise AttributeMissingException('The attribute, "fields", is invalid or missing')

        if fields is None or lookup_SQL is None:
            raise AttributeMissingException('This stanza is not valid')

        # a brute way to make input fields to be valid
        ui_input_spl_search = 'index=_internal | head 100 | stats count by sourcetype |'
        ui_input_spl_search += ' | '.join(['eval {}="changeme"'.format(field) for field in input_fields])

        ui_field_column_map = json.dumps([{"name":field,
                                           "selected": True,
                                           "removable": True,
                                           "label": field,
                                           "value": field,
                                           "alias": field} for field in input_fields])
        ui_column_output_map = json.dumps([{"name": field} for field in output_fields])

        # safe to assume that the connection name == database name since that is now connection is migrated
        entity.set(lookupSQL=lookup_SQL)
        entity.set(input_fields=','.join(input_fields),
                   output_fields=','.join(output_fields),
                   connection=self.src.content.get('database'),
                   ui_is_auto_lookup=0,
                   ui_query_mode='advanced',
                   ui_input_spl_search=ui_input_spl_search,
                   ui_field_column_map=ui_field_column_map,
                   ui_column_output_map=ui_column_output_map)

        entity.filter_attrs('description',
                            'lookupSQL',
                            'updateSQL',
                            'reloadSQL',
                            'policy',
                            'connection',
                            'key_pattern',
                            'input_fields',
                            'output_fields',
                            'ui_query_mode',
                            'ui_query_catalog',
                            'ui_query_schema',
                            'ui_query_table',
                            'ui_input_spl_search',
                            'ui_input_saved_search',
                            'ui_use_saved_search',
                            'ui_is_auto_lookup',
                            'ui_query_result_columns',
                            'ui_column_output_map',
                            'ui_field_column_map')

    def validate(self):
        pass

    def teardown(self):
        pass

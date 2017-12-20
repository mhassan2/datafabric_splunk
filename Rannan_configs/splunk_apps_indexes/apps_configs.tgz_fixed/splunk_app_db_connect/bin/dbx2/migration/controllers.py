import json

import splunk.rest as rest
import splunk.entity as en

from splunk import ResourceNotFound

from dbx2.exceptions import ResourceNotFoundException, InvalidState, ValidationFailedException, ResourceExistsException
from dbx2.utils import trace
from dbx2.migration import get_available_migrations


from dbx2.dbx_logger import logger
NAMESPACE = 'splunk_app_db_connect'
OWNER = 'nobody'

class MigrationConf(object):
    """
    responsible for reading/writing of migration.conf
    """
    def __init__(self, migration_id, session_key):
        self.migration_id = migration_id
        self.session_key = session_key

        try:
            entity = en.getEntity(['configs', 'conf-app-migration'], self.migration_id, namespace=NAMESPACE,
                                  owner=OWNER, sessionKey=self.session_key)
        except ResourceNotFound:
            raise ResourceNotFoundException('"%s" is not found in migration.conf', self.migration_id)

        try:
            self._state = json.loads(entity['STATE'])
        except KeyError:
            # if STATE does not exist yet
            self._state = {}
        except ValueError:
            # if "json" throws a fit, that means the value is not in JSON
            raise InvalidState('STATE is malformed. It must be in JSON format')

        self._dest_conf = entity.get('DEST_CONF', migration_id)

    @property
    def dest_conf(self):
        return self._dest_conf

    def get_state(self, entity):
        """
        get the state for an entity. If the entity does not exist, return 0
        """
        return self._state.get(entity, 0)

    def update_state(self, entity, state):
        """
        updates the state but this actually writes the entire content of the entity
        """
        self._state[entity] = state
        contents = {
            'STATE': json.dumps(self._state)
        }

        entity_path = ["configs", "conf-app-migration"]
        entity = en.Entity(entity_path, self.migration_id, contents=contents,
                           namespace=NAMESPACE,
                           owner=OWNER)

        # to bypass a funny check in getFullPath
        entity['eai:acl'] = {}
        en.setEntity(entity, sessionKey=self.session_key)


class MigrationController(object):
    """
    facilitates migration as specified in the process flow diagram
    (https://confluence.splunk.com/display/PROD/DBX2+Migration+Specifications#DBX2MigrationSpecifications-ProcessFlow)
    """
    def __init__(self, migration_id, resource_url, session_key):
        """
        :param migration_id: the migration entity e.g.) "identity"
        :param from_resource: the fully qualifying endpoint that describes the resource
        e.g.) /nobody/dbx/configs/conf-database/mysql_user1
        :param session_key: the user session key
        """
        logger.info("Migration Controller: __init__(%s, %s, %s", migration_id, resource_url, session_key)
        self.migration_id = migration_id
        self.resource_url = resource_url
        self.session_key = session_key
        self.entity_entry = None

        self._load_from_resource()
        self._load_migration_conf()

    @trace
    def _load_from_resource(self):
        """
        fetch SplunkEntity identified by self.from_resource, and use it to
        populate our initial state entity (sets self.entity)
        """

        url = self.resource_url
        response, content = rest.simpleRequest(url, sessionKey=self.session_key,
                                               rawResult=True,
                                               getargs={'output_mode': 'json'})
        if response.status == 200:
            self.entity = json.loads(content)['entry'][0]
        else:
            raise ResourceNotFoundException('%s is an invalid path to an entity.', url)


    @trace
    def _load_migration_conf(self):
        """
        loads the migration policy as well as the state of all previous migrations
        stored in conf-app-migration/<migrationId>. We will need this to guide our requested
        migration. The migration.conf will be updated at the end of a successful migration
        to indicate the new migration level for each of the migrated entities
        """

        self.migration_conf = MigrationConf(self.migration_id, self.session_key)

    @trace
    def _get_available_migrations(self, min_level=1):
        """
        fetch all available migrations; self.migrations
        """
        return get_available_migrations(self.migration_id, min_level=min_level)

    @trace
    def backup(self):
        """
        A backup on the filesystem will be created with the timestamp as a suffix. this guarantees there will be
        a recovery path in case of catastrophic failure
        """
        pass

    @trace
    def migrate(self, force=False):
        """
        iterates over available migrations and invokes run() and apply() methods

        :returns a MigrationEntity JSON representation and None if there is no migration to run
        """

        # we are going to assume that there is only one migration level at this time
        # and if force is true, we always set min_level to 1 so that we can force
        # migration to run again even if it was run previously.
        if force:
            min_level = 1
        else:
            state = self.migration_conf.get_state(self.resource_url)

            try:
                min_level = int(state) + 1
            except ValueError:
                raise InvalidState("%s is not an integer", state)

        migrations = self._get_available_migrations(min_level=min_level)

        last_migration = None

        for migration_class in migrations:
            # if no migration was run before, we start from the resource we just loaded
            # otherwise, we use the resulting entity from the previous migration
            if last_migration is None:
                conf_name = self.migration_id
                stanza_name = self.entity['name']
                content = self.entity['content']
            else:
                conf_name = last_migration.dst.conf
                stanza_name = last_migration.dst.name
                content = last_migration.content

            migration = migration_class(conf_name, stanza_name, content)

            self._run(migration)
            last_migration = migration

        # if migration ran, we apply the migration
        if last_migration:
            self._apply(last_migration, force=force)
            return last_migration.dst

        # if no migration ran, return None
        return None

    @trace
    def _run(self, migration):
        """
        invokes setup() and migrate() of an available migration plugin instance
        """
        migration.setup(session_key=self.session_key)
        migration.migrate()

    @trace
    def _apply(self, migration, force=False):
        """
        invokes validate() and teardown() of an available migration plugin instance
        """
        try:
            migration.validate()
            migration.teardown()
        except Exception as e:
            self.rollback()
            raise e
        else:
            # migration.dst is the resulting entity after the migration is applied
            dst_entity = migration.dst

            entity_path = self.migration_conf.dest_conf

            update = False
            uri = en.buildEndpoint(entity_path, entityName=dst_entity.name, namespace=NAMESPACE, owner=OWNER)

            if self._check_resource_exists(uri, sessionKey=self.session_key):
                if force:
                    update = True
                else:
                    raise ResourceExistsException

            if update:
                entity = en.Entity(entity_path, dst_entity.name,
                                   namespace=NAMESPACE,
                                   contents=dst_entity.content,
                                   owner=OWNER)
            else:
                entity = en.Entity(entity_path, '_new',
                                   namespace=NAMESPACE,
                                   contents=dst_entity.content,
                                   owner=OWNER)
                entity['name'] = dst_entity.name

            # to bypass a funny check in splunk.entity.getFullPath()
            entity['eai:acl'] = {}

            en.setEntity(entity, sessionKey=self.session_key)

            self.migration_conf.update_state(self.resource_url, migration.migration_level)

    def _check_resource_exists(self, uri, sessionKey):
        '''
        replaces rest.checkResourceExists since it has a serious bug not catching the status code 500
        '''
        try:
            server_response, server_content = rest.simpleRequest(uri, sessionKey)
            if server_response.status == 200:
                return True
        except:
            pass

        return False

    @trace
    def rollback(self):
        pass

import argparse
import getpass
import sys
import splunk

from splunk import auth
from splunk import entity as en

from dbx2.migration.controllers import MigrationController
from dbx2.exceptions import ResourceExistsException, EntityCanNotBeMigrated


class MigrateCommand(object):
    '''
    helper class to run migration scripts from the command line
    '''
    def __init__(self, username=None, password=None, session_key=None):
        self.session_key = session_key if session_key else auth.getSessionKey(username, password)

    def migrate(self, src_endpoint, migration_ids, filter=None, force=False):
        entities = en.getEntities(src_endpoint, namespace='dbx', owner='nobody', search=filter, count=0)

        if not entities:
            print "No entity found"
            return

        # iterate source entires
        for key, entity in entities.iteritems():
            for migration_id in migration_ids:

                path = en.buildEndpoint(entity.path, entityName=entity.name, namespace='dbx', owner='nobody')
                controller = MigrationController(migration_id, path, self.session_key)

                try:
                    result = controller.migrate(force=force)
                    if result is None:
                        print "{} of {} has been migrated already. Use --force to overwrite.".format(migration_id, path)
                    else:
                        print "{} of {} has been migrated with following attributes:\n".format(migration_id, path)
                        self.pretty_print(result)

                except ResourceExistsException:
                    print "{} already exists in {} for DB Connect 2. Use --force to overwrite.".format(key, migration_id)

                except EntityCanNotBeMigrated:
                    pass

                except Exception as e:
                    print "an exception occurred while migrating {} from {}: {}".format(migration_id, path, e)

    def pretty_print(self, entity):
        print '> [{}]'.format(entity.name)

        # sort the attribute - it just looks much better
        for name, value in sorted(entity.content.iteritems(), key=lambda key: key[0]):
            print '> {}: {}'.format(name, value)

        print ''


def migrate(migration_name, endpoint, migration_ids):

    parser = argparse.ArgumentParser(description='Migrates {} entities from DB Connect 1 to DB Connect 2.'.format(migration_name))
    parser.add_argument('-u', '--user', help='admin username')
    parser.add_argument('-p', '--password', help='admin password')
    parser.add_argument('-f', '--filter', help='run only entities of which names match FILTER (standard Splunk filter)')
    parser.add_argument('--force', action='store_true', help='force overwriting')

    args = parser.parse_args()

    user = args.user
    if user is None:
        print 'username: ',
        user = sys.stdin.readline().rstrip()

    password = args.password
    if password is None:
        password = getpass.getpass()

    if user is None or password is None:
        print 'username and password are required!'
        return

    try:
        migrate_cmd = MigrateCommand(user, password)
        migrate_cmd.migrate(endpoint, migration_ids, filter=args.filter, force=args.force)

    except splunk.AuthenticationFailed:
        print "Incorrect username or password. Authentication Failed"
    except splunk.AuthorizationFailed:
        print "Insufficient privilege."
    except splunk.SplunkdConnectionException:
        print "Connection Failed. Is Splunkd daemon running?"
    except Exception as e:
        print "An error occured: {}".format(e)

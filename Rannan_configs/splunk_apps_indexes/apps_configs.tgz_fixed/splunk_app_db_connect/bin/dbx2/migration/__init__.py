from importlib import import_module
import json
import os
import abc
import inspect
import re

from dbx2.decorators import freezable
from dbx2.dbx_logger import logger


MIGRATION_FILE_REGEX = r'(\d{3}\d*)_.*\.py$'


class AbstractMigration(object):
    """
    An abstract class to support app migration. Classes that implement this class must have the filename that satisfies
    \d{3}_*\.py.
    """
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def migration_level(self):
        """
        return the migration level ranging [001-999] by retrieving it from the file that instantiated class
        belongs to
        """

    @abc.abstractmethod
    def setup(self, session_key=None):
        """
        performs any operation required prior to invoking the migrate method
        """

    @abc.abstractmethod
    def migrate(self):
        """
        invokes transformation methods on self.dest entity. upon return from this method , expect that self.dest will be
        in the desired state for persisting to disk
        """

    @abc.abstractmethod
    def validate(self):
        """
        executes after all migrate() operations are successful. Throws ValidationFailedException when validation fails
        """

    @abc.abstractmethod
    def teardown(self):
        """
        performs any needed cleanup
        """


class BaseMigration(AbstractMigration):
    """
    A base class that should be implemented by a custom migration class
    """

    @property
    def migration_level(self):
        """
        return the migration level ranging [001-999] by retrieving it from the file that instantiated class
        belongs to
        """
        filename = os.path.basename(inspect.getsourcefile(self.__class__))
        result = re.match(MIGRATION_FILE_REGEX, filename)
        if result is None:
            raise Exception('The filename must start with a migration level ex) 001_example.py')

        level = int(result.group(1))
        if level < 1 or level > 999:
            raise Exception('The migration level must be within 001-999')

        return level

    def __init__(self, conf, stanza_name, content):
        self.src = MigrationEntity(conf=conf, name=stanza_name, content=content)
        self.dst = MigrationEntity(conf=conf, name=stanza_name, content=content)



class MigrationEntity(object):
    """
    MigratrionEntity holds information of a "migration entity" which points a key/val pair in a .conf file.

    This entity can be represented as JSON as follows:
    {
        // name of conf file
        conf: "identity",
        // name of stanza
        name: "mySecretIdentity",
        // content
        content: {
            user: "mkinsley",
            password: "enc:ptPuAD1fz+KArUgV+82kIA=="
        }
    }
    """

    def __init__(self, conf=None, name=None, content=None):
        self.conf = conf
        self.name = name
        self.content = {} if content is None else content
        self._frozen = False

    def freeze(self):
        """
        freezes the entity so that none of the transformation method has any effect
        """
        self._frozen = True

    @freezable
    def rename(self, new_name):
        """ renames the stanza name with new_name and returns self """
        self.name = new_name
        return self

    @freezable
    def rename_conf(self, conf_name):
        """ renames conf with conf_name and returns self """
        self.conf = conf_name
        return self

    @freezable
    def set(self, **kwargs):
        """

        sets attributes defined in **kwargs and returns self

        ex) entity.set(user="mkinsley", "enc:ptPuAD1fz+KArUgV+82kIA==", ...)

        """
        for key, value in kwargs.iteritems():
            if value is not None:
                self.content[key] = value
        return self

    @freezable
    def filter_attrs(self, *args):
        """
        keep only attributes that match the list of attributes given by *args and returns self

        new_entity = entity.filter("user")
        """

        self.content = {key: self.content[key] for key in args if key in self.content}
        return self

    @freezable
    def unset(self, attr):
        """ remove an attribute and returns self """
        if attr in self.content:
            del self.content[attr]

        return self

    @freezable
    def reject_attrs(self, *args):
        """
        remove attributes that match the list of attributes given by *args and returns self
        """

        for key in args:
            self.unset(key)

        return self

    def __repr__(self):
        return self.to_json()

    def to_json(self):
        return json.dumps({
            'conf': self.conf,
            'name': self.name,
            'content': self.content
        })


def is_subclass_by_name(child, parent_name):
    """
    return True if child has a parent whose name is "parent_name"

    issubclass does not work if the parent is loaded via import module
    """
    if inspect.isclass(child):
        if parent_name in [ancestor.__name__ for ancestor in inspect.getmro(child)[1:]]:
            return True
    return False


def get_available_migrations(migration_id, min_level=1):
    """
    looks for migration modules in the "migration_id" submodule
    :param migration_id: the name of the submodule under dbx2.migration.migrations
    :param min_level: the minimum migration level (inclusive)
    :return: modules of migration classes with the migration level greater than or equal to min_level
    """

    current_dir = os.path.dirname(os.path.realpath(__file__))
    migration_path = os.path.join(current_dir, 'migrations', migration_id)

    r = re.compile(MIGRATION_FILE_REGEX)
    results = []

    for root, directories, filenames in os.walk(migration_path):

        # get the module name
        module_name = __name__ + root[len(current_dir):].replace(os.sep, '.')

        for filename in filter(r.match, filenames):
            # first three digits represent the migration level
            migration_level = int(filename[:3])

            if migration_level < min_level:
                continue

            # strip .py
            module = import_module(module_name + '.' + filename[:-3])
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and is_subclass_by_name(obj, 'BaseMigration'):
                    results.append((migration_level, obj,))

    sorted_result = sorted(results, key=lambda x: x[0])
    return [obj for migration_level, obj in sorted_result]

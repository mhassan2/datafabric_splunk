class ResourceNotFoundException(Exception):
    """
    An expected entity was not found
    """
    pass


class ResourceExistsException(Exception):
    """
    An entity was unexpectedly found
    """
    pass


class ResourceDisabledException(Exception):
    """
    An entity was expected to be disabled but was not
    """
    pass


class AttributeMissingException(Exception):
    """
    An attribute on an entity was expected but not found
    """
    pass


class ValidationFailedException(Exception):
    """
    Validation failed
    """
    pass


class AttributeExistsException(Exception):
    """
    Tried to add an attribute that already exists
    """
    pass


class MigrationEntityFrozenException(Exception):
    """
    Transformation attempted when the migration entity is frozen
    """
    pass


class EntityCanNotBeMigrated(Exception):
    """
    an entity is not appropriate for a particular migration
    """
    pass

class InvalidState(Exception):
    """
    migration.conf has the invalid state
    """
    pass
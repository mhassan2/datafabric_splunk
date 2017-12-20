from dbx2.exceptions import MigrationEntityFrozenException


def freezable(func):
    """
    Used to mark a method on MigrationEntity to disable a method if the class is frozen
    """
    def wrapper(self, *args, **kwargs):
        from dbx2.migration import MigrationEntity
        assert isinstance(self, MigrationEntity)

        if self._frozen:
            raise MigrationEntityFrozenException()

        return func(self, *args, **kwargs)

    return wrapper

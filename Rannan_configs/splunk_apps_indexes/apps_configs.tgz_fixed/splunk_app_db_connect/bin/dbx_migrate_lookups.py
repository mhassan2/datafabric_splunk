from dbx2.migration.migrate import migrate


ENDPOINT = 'configs/conf-dblookup'


if __name__ == '__main__':
    migrate('lookup', ENDPOINT, ['lookup'])

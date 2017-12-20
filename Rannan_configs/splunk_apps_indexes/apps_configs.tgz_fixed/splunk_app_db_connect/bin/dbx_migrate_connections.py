from dbx2.migration.migrate import migrate


ENDPOINT = 'configs/conf-database'


if __name__ == '__main__':
    migrate('Database Connections', ENDPOINT, ['identity', 'connection'])

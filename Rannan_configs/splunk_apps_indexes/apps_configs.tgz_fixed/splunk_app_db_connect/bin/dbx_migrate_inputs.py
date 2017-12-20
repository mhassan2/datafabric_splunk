from dbx2.migration.migrate import migrate


ENDPOINT = 'configs/conf-inputs'


if __name__ == '__main__':
    migrate('inputs', ENDPOINT, ['input'])

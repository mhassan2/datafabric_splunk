# Copyright (C) 2005-2016 Splunk Inc. All Rights Reserved.
# The file contains the specification for database connections

[<name>]

serviceClass = <string>
# optional
# inherits from db_connection_types.conf if not configured
# java class that serves the jdbc service for this type.


customizedJdbcUrl = <string>
# optional
# the user customized jdbc url used to connect to database, empty or missing means use template to generate jdbc url.
# see jdbcUrlFormat and jdbcUrlSSLFormat defined in db_connection_types.conf.spec


jdbcUseSSL = [true | false]
# optional
# inherits from db_connection_types.conf if not configured
# default is false, whether this type of connection will support SSL connection.



jdbcDriverClass = <string>
# optional
# inherits from db_connection_types.conf if not configured
# java jdbc vendor driver class.



testQuery = <string>
# optional
# inherits from db_connection_types.conf if not configured, if still not provided, JDBC isValid API will be used.
# simple SQL to test validation for this database type.



database = <string>
# required only when other parameters refer to.
# inherits from db_connection_types.conf if not configured
# The default database that the connection will use



connection_type = <string>
# required
# The type of connection configured in db_connection_types.conf that the connection refer to



identity = <string>
# required
# The database identity that the connection will use when connecting to the database
# an identity provides username and password for database connection.



isolation_level = <string>
# optional
# The transaction isolation level that the connection should use
# valid values are: TRANSACTION_NONE, TRANSACTION_READ_COMMITTED, TRANSACTION_READ_UNCOMMITTED, TRANSACTION_REPEATABLE_READ, TRANSACTION_SERIALIZABLE and DATABASE_DEFAULT_SETTING
# default: DATABASE_DEFAULT_SETTING.



readonly = true|false
# optional
# default to false
# Whether the database connection is read-only. If it is readonly, any modifying SQL statement will be blocked



host = <string>
# required only when other parameters refer to.
# The host name or IP of the database server for the connection
# Possible variable from jdbcUrlFormat.



port = <integer>
# required only when other parameters refer to.
# inherits from db_connection_types.conf if not configured
# The TCP port number that the host database server is listening to for connections
# Possible variable from jdbcUrlFormat.


informixserver = <string>
# optional
# Required option for informix server to compose proper jdbc connection url.
# This attribute is used for informix server connection setup only.


useConnectionPool = true|false
# optional
# boolean to make connection use a connection pool
# defaults to true



connection_properties = <string>
# optional, differs via different databases.


fetch_size = <integer>
# optional, default is 100, the number of rows retrieved with each trip to the database.


maxConnLifetimeMillis = <value>
# optional, default is 120000 = 120 seconds
# valid when useConnectionPool = true
# The maximum lifetime in milliseconds of a connection. After this time is exceeded the connection will fail the next activation, passivation or validation test.
# A value of zero or less means the connection has an infinite lifetime.


maxWaitMillis = <value>
# optional, default is 30000 = 30 seconds
# valid when useConnectionPool = true
# The maximum number of milliseconds that the pool will wait (when there are no available connections) for a connection to be returned before throwing an exception.
# [250, 300000] milliseconds is a reasonable value to wait to establish a connection.  The max wait time is 300000 millisenconds (300 seconds).



maxTotalConn = <value>
# optional, default is 8 connections
# valid when useConnectionPool = true
# The maximum number of active connections that can be allocated from this pool at the same time, or negative for no limit.

timezone = <time zone identifier>
# optional, default uses JVM time zone
# The identifier could be:
# an offset from UTC/Greenwich, that uses the same offset regardless given date-time e.g. +08:00
# an area where a specific set of rules for finding the offset from UTC/Greenwich apply e.g. Europe/Paris.

localTimezoneConversionEnabled = [true | false]
# optional, default is false
# valid when a time zone is set
# When turned on, time-related fields are read from the DB using the configured time zone and then translated to the JVM time zone.
# For example, with a DB using UTC and the JVM using GMT+8, the datetime field defined in the DB
# 2017-07-21 08:00:00 will be displayed 2017-07-21 16:00:00

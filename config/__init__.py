# Enable PyMySQL fallback as MySQLdb if installed (ideal for Render & TiDB Cloud)
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

# TiDB Cloud reports version 8.0.11 (MySQL 8.0 protocol).
# Modern Django artificially requires MySQL >= 8.4. Bypass this strict version check for TiDB compatibility.
try:
    from django.db.backends.mysql.base import DatabaseWrapper
    DatabaseWrapper.check_database_version_supported = lambda self: None
except ImportError:
    pass

# TiDB Cloud DDL engine does not allow adding a column and an inline FOREIGN KEY constraint
# referencing that same new column in a single ALTER TABLE statement (OperationalError 1072).
# Setting sql_create_column_inline_fk to None forces Django to execute ADD COLUMN first,
# followed by a separate ALTER TABLE ADD CONSTRAINT, which TiDB fully supports.
try:
    from django.db.backends.mysql.schema import DatabaseSchemaEditor
    DatabaseSchemaEditor.sql_create_column_inline_fk = None
except ImportError:
    pass

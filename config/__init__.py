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

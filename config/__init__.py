# Enable PyMySQL fallback as MySQLdb if installed (ideal for Render & TiDB Cloud)
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

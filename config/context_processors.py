from django.db import connection


def db_health_status(request):
    """
    MariaDB Health Check context processor.
    Pings the default database connection and returns whether it is healthy.
    """
    db_healthy = False
    try:
        connection.ensure_connection()
        if connection.is_usable():
            db_healthy = True
    except Exception:
        db_healthy = False

    return {
        'db_healthy': db_healthy,
    }

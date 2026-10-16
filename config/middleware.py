from django.db import connection
from django.db.utils import OperationalError, DatabaseError
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import render


class DatabaseHealthMiddleware:
    """
    Middleware that monitors database availability and ensures graceful degradation.
    When MariaDB/MySQL is offline:
    1. Sets request.db_healthy = False.
    2. Overrides request.user with AnonymousUser() to prevent lazy auth/session lookups
       from triggering an unhandled OperationalError in templates.
    3. Catches any OperationalError during view processing or rendering and returns
       a clean offline response instead of a crash.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        db_healthy = True
        try:
            connection.ensure_connection()
            if not connection.is_usable():
                db_healthy = False
        except (OperationalError, DatabaseError, Exception):
            db_healthy = False

        request.db_healthy = db_healthy

        if not db_healthy:
            request.user = AnonymousUser()
            if hasattr(request, 'session'):
                request.session.modified = False
        else:
            # If DB currently seems reachable, safeguard lazy user lookup against sudden disconnects
            if hasattr(request, 'user') and hasattr(request.user, '_setupfunc'):
                orig_setup = request.user._setupfunc

                def safe_setup():
                    try:
                        return orig_setup()
                    except (OperationalError, DatabaseError, Exception):
                        request.db_healthy = False
                        return AnonymousUser()

                request.user._setupfunc = safe_setup

        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, (OperationalError, DatabaseError)):
            request.db_healthy = False
            request.user = AnonymousUser()

            # For home page, render home page with empty context and topbar showing "БД не активна"
            if request.path == '/':
                context = {
                    'components_count': 0,
                    'categories_count': 0,
                    'locations_count': 0,
                    'suppliers_count': 0,
                    'projects_count': 0,
                    'popular_categories': [],
                    'recent_components': [],
                    'db_healthy': False,
                }
                return render(request, 'home.html', context)

            # For other pages, render 503 offline notification
            context = {
                'db_healthy': False,
                'error_message': 'Сервер бази даних MariaDB наразі не активний (127.0.0.1:3306).',
            }
            return render(request, '503_db_offline.html', context, status=503)

        return None

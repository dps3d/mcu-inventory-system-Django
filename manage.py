#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # Auto-switch to project virtualenv if running with system python
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(base_dir, '.venv', 'bin', 'python')
    if (
        sys.prefix == getattr(sys, 'base_prefix', sys.prefix)
        and os.path.exists(venv_python)
        and os.path.abspath(sys.executable) != os.path.abspath(venv_python)
    ):
        os.execv(venv_python, [venv_python] + sys.argv)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

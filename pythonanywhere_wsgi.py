# +++++++++++ DJANGO +++++++++++
# To use your own django app use code like this:
import os
import sys

# add your project directory to the sys.path
project_home = os.environ.get('PROJECT_HOME', os.path.dirname(os.path.abspath(__file__)))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# set environment variable to tell django where your settings.py is
os.environ['DJANGO_SETTINGS_MODULE'] = 'admin_panel.settings'

# serve django via WSGI
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

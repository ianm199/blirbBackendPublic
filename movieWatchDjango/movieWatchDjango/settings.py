import os

if 'DJANGO_SETTINGS' in os.environ and os.environ['DJANGO_SETTINGS'] == "prod":
    print("PRODUCTION SERVER")
    from .settings_prod import *
else:
    print("DEVELOPMENT SERVER")
    from .settings_dev import *

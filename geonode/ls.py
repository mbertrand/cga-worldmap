
GEONODE_APPS = (
    # GeoNode internal apps
    'geonode.people',
    'geonode.base',
    'geonode.layers',
    'geonode.maps',
    'geonode.proxy',
    'geonode.security',
    'geonode.social',
    'geonode.catalogue',
    'geonode.documents',
    'geonode.api',
    'geonode.search',

    # GeoNode Contrib Apps
    'geonode.contrib.services',
    'geonode.contrib.groups',
    'geonode.contrib.dynamic',

    # GeoServer Apps
    # Geoserver needs to come last because
    # it's signals may rely on other apps' signals.
    'geonode.geoserver',
    'geonode.upload',
)

WORLDMAP_APPS = (
    'geonode.worldmap',
    'geonode.worldmap.core',
    'geonode.worldmap.profile',
    'geonode.worldmap.register',
    'geonode.worldmap.mapnotes',
    'geonode.worldmap.capabilities',
    'geonode.worldmap.layers',
    'geonode.worldmap.maps',
    'geonode.worldmap.proxy',
    'geonode.worldmap.security',
    'geonode.worldmap.stats',
    'geonode.worldmap.hoods',
    'geonode.worldmap.gazetteer',
    'geonode.worldmap.queue',
)

INSTALLED_APPS = (

                     # Apps bundled with Django
                     'django.contrib.auth',
                     'django.contrib.contenttypes',
                     'django.contrib.sessions',
                     'django.contrib.sites',
                     'django.contrib.admin',
                     'django.contrib.sitemaps',
                     'django.contrib.staticfiles',
                     'django.contrib.messages',
                     'django.contrib.humanize',
                     'django.contrib.gis',

                     # Third party apps

                     # Utility
                     'pagination',
                     'taggit',
                     'taggit_templatetags',
                     'friendlytagloader',
                     'geoexplorer',
                     'leaflet',
                     'django_extensions',
                     'modeltranslation',
                     'autocomplete_light',
                     'tastypie',
                     'polymorphic',

                     # Theme
                     "pinax_theme_bootstrap_account",
                     "pinax_theme_bootstrap",
                     'django_forms_bootstrap',

                     # Social
                     'account',
                     'avatar',
                     'dialogos',
                     'agon_ratings',
                     'notification',
                     'announcements',
                     'actstream',
                     'user_messages',

                     # Queue
                     'djcelery',
                     'djkombu',

                     #Debugging
                     #'debug_toolbar',
                 ) + GEONODE_APPS + WORLDMAP_APPS


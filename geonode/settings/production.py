from .base import * 

# Enter production settings here
SITENAME = "GeoNode"

SITEURL = "http://107.22.231.227/"

# The FULLY QUALIFIED url to the GeoServer instance for this GeoNode.
GEOSERVER_BASE_URL = SITEURL + "geoserver/"

# The FULLY QUALIFIED url to the GeoNetwork instance for this GeoNode
GEONETWORK_BASE_URL = SITEURL + "geonetwork/"

OGP_URL = "http://geodata.tufts.edu/solr/select"
HGL_VALIDATION_KEY="OPENGEOPORTALROCKS"



# Enter production settings
USE_QUEUE = True
QUEUE_INTERVAL = '*/10'
CELERY_IMPORTS = ("geonode.queue", )
BROKER_URL = "django://"
if USE_QUEUE:
    import djcelery
    djcelery.setup_loader()


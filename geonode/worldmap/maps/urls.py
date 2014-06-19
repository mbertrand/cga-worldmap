from django.conf.urls import patterns, url, include
from geonode.maps.urls import urlpatterns as mappatterns

urlpatterns = patterns('geonode.maps.views',
      url(r'^(?P<mapid>\d+)/data$', 'map_json', name='map_json'),
      url(r'^new/data$', 'new_map_json', name='new_map_json'),
)

urlpatterns = patterns('geonode.worldmap.maps.views',
    (r'^checkurl/?$', 'ajax_url_lookup'),
    (r'^history/(?P<mapid>\d+)/?$', 'ajax_snapshot_history'),
    url(r'^new$', 'new_map', name="new_map"),
    url(r'^print$', 'printmap', name='printmap'),
    (r'^snapshot/create/?$', 'snapshot_create'),
    (r'^addgeonodelayer/?$', 'addLayerJSON'),
    (r'^(?P<mapid>[^/]+)/?$', 'map_view'),
    (r'^(?P<mapid>[^/]+)/info$', 'map_detail'),
    (r'^(?P<mapid>[^/]+)/embed/?$', 'embed'),
    (r'^(?P<mapid>[^/from_v]+)/mobile/?$', 'mobilemap'),
    (r'', include('geonode.maps.urls')),
    (r'^(?P<mapid>[^/]+)/(?P<snapshot>[A-Za-z0-9_\-]+)/?$', 'map_view'),
    (r'^(?P<mapid>[^/]+)/(?P<snapshot>[A-Za-z0-9_\-]+)/info$', 'map_detail'),
    (r'^(?P<mapid>[^/]+)/(?P<snapshot>[A-Za-z0-9_\-]+)/embed/?$', 'embed'),
    (r'^(?P<mapid>[^/]+)/(?P<snapshot>[A-Za-z0-9_\-]+)/mobile/?$', 'mobilemap'),
    url(r'^(?P<mapid>[^/]+)/?$', 'map_view', name='map_view'),
    url(r'^(?P<mapid>[^/]+)/info$', 'map_detail', name='map_detail'),
)

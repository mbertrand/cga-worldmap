# Create your views here.
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.contrib.auth.decorators import login_required
from django.utils import simplejson as json
import logging
import re
from geonode.documents.models import get_related_documents
import httplib2
from geonode.security.enumerations import AUTHENTICATED_USERS, ANONYMOUS_USERS
from geonode.maps.models import Map, MapLayer
from geonode.maps.views import _resolve_map, map_json as basemap_json, new_map_config, map_detail
from geonode.maps.views import MAP_LEV_NAMES, _PERMISSION_MSG_GENERIC, _PERMISSION_MSG_LOGIN, _PERMISSION_MSG_VIEW
from geonode.security.views import _perms_info
from geonode.utils import resolve_object, ogc_server_settings
from geonode.layers.models import Layer
from geonode.worldmap.profile.forms import ContactProfileForm
from geonode.maps.models import MapSnapshot
from geonode.encode import num_encode, num_decode
from geonode.worldmap.stats.models import MapStats
from geonode.worldmap.security.views import _perms_info_email_json
from geonode.utils import layer_from_viewer_config
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger("geonode.worldmap.maps.views")

@csrf_exempt
def addLayerJSON(request):
    logger.debug("Enter addLayerJSON")
    layername = request.POST.get('layername', False)
    logger.debug("layername is [%s]", layername)

    if layername:
        try:
            layer = Layer.objects.get(typename=layername)
            if not request.user.has_perm("layers.view_layer", obj=layer):
                return HttpResponse(status=401)
            maplayer = MapLayer(name=layer.typename, local=True)
            sfJSON = {'layer': maplayer.layer_config(request.user)}
            logger.debug('sfJSON is [%s]', str(sfJSON))
            return HttpResponse(json.dumps(sfJSON))
        except Exception, e:
            logger.debug("Could not find matching layer: [%s]", str(e))
            return HttpResponse(str(e), status=500)

    else:
        return HttpResponse(status=500)


def _resolve_map_custom(request, id, fieldname, permission='maps.change_map',
                 msg=_PERMISSION_MSG_GENERIC, **kwargs):
    '''
    Resolve the Map by the provided typename and check the optional permission.
    '''
    return resolve_object(request, Map, {fieldname:id}, permission = permission,
                          permission_msg=msg, **kwargs)


def map_view(request, mapid, snapshot=None, template='maps/map_view.html'):
    """
    The view that returns the map composer opened to
    the map with the given map ID.
    """

    if not mapid.isdigit():
        map_obj = _resolve_map_custom(request, mapid, 'urlsuffix', 'maps.view_map', _PERMISSION_MSG_VIEW)
    else:
        map_obj = _resolve_map(request, mapid, 'maps.view_map', _PERMISSION_MSG_VIEW)
    
    if snapshot is None:
        config = map_obj.viewer_json(request.user)
    else:
        config = snapshot_config(snapshot, map_obj, request.user)
    
    config['edit_map'] = request.user.has_perm('maps.change_map', obj=map_obj)
    config['db_datastore'] = ogc_server_settings.DATASTORE
    return render_to_response(template, RequestContext(request, {
        'config': json.dumps(config),
        'title': map_obj.title,
        'DB_DATASTORE' : ogc_server_settings.DATASTORE,
        'USE_GAZETTEER' : settings.USE_GAZETTEER,
        'urlsuffix': get_suffix_if_custom(map_obj)
    }))

def map_detail(request, mapid, template='maps/map_detail.html'):
    if not mapid.isdigit():
        map_obj = _resolve_map_custom(request, mapid, 'urlsuffix', 'maps.view_map', _PERMISSION_MSG_VIEW)
    else:
        map_obj = _resolve_map(request, mapid, 'maps.view_map', _PERMISSION_MSG_VIEW)

    map_obj.popular_count += 1
    map_obj.save()

    config = map_obj.viewer_json(request.user)
    config = json.dumps(config)
    layers = MapLayer.objects.filter(map=map_obj.id)
    return render_to_response(template, RequestContext(request, {
        'config': config,
        'map': map_obj,
        'layers': layers,
        'permissions_json': json.dumps(_perms_info(map_obj, MAP_LEV_NAMES)),
        "documents": get_related_documents(map_obj),
        'urlsuffix': get_suffix_if_custom(map_obj)
        }))


def clean_config(conf):
    if isinstance(conf, basestring):
        config = json.loads(conf)
        config_extras = ["tools", "rest", "homeUrl", "localGeoServerBaseUrl", "localCSWBaseUrl", "csrfToken", "db_datastore", "authorizedRoles"]
        for config_item in config_extras:
            if config_item in config:
                del config[config_item ]
            if config_item in config["map"]:
                del config["map"][config_item ]
        return json.dumps(config)
    else:
        return conf


def new_map(request, template='maps/map_view.html'):
    config = json.loads(new_map_config(request))
    config['edit_map'] = True
    config['db_datastore'] = ogc_server_settings.DATASTORE
    if isinstance(config, HttpResponse):
        return json.dumps(config)
    else:
        return render_to_response(template, RequestContext(request, {
            'config': json.dumps(config),
            'DB_DATASTORE' : ogc_server_settings.DATASTORE,
            'USE_GAZETTEER' : settings.USE_GAZETTEER
        }))


def ajax_map_permissions(request, mapid, use_email=False):
    map_obj = get_object_or_404(Map, pk=mapid)

    if not request.user.has_perm("maps.change_map_permissions", obj=map_obj):
        return HttpResponse(
            'You are not allowed to change permissions for this map',
            status=401,
            mimetype='text/plain'
        )

    if not request.method == 'POST':
        return HttpResponse(
            'You must use POST for editing map permissions',
            status=405,
            mimetype='text/plain'
        )

    spec = json.loads(request.body)
    map_obj.set_permissions(map_obj, spec, use_email)

def ajax_map_permissions_by_email(request, mapid):
    return ajax_map_permissions(request, mapid, True)

def ajax_url_lookup(request):
    if request.method != 'POST':
        return HttpResponse(
            content='ajax user lookup requires HTTP POST',
            status=405,
            mimetype='text/plain'
        )
    elif 'query' not in request.POST:
        return HttpResponse(
            content='use a field named "query" to specify a prefix to filter urls',
            mimetype='text/plain'
        )
    if request.POST['query'] != '':
        forbiddenUrls = ['new','view',]
        maps = Map.objects.filter(urlsuffix__startswith=request.POST['query'])
        if request.POST['mapid'] != '':
            maps = maps.exclude(id=request.POST['mapid'])
        json_dict = {
            'urls': [({'url': m.urlsuffix}) for m in maps],
            'count': maps.count(),
            }
    else:
        json_dict = {
            'urls' : [],
            'count' : 0,
            }
    return HttpResponse(
        content=json.dumps(json_dict),
        mimetype='text/plain'
    )

def snapshot_config(snapshot, map_obj, user):
    """
        Get the snapshot map configuration - look up WMS parameters (bunding box)
        for local GeoNode layers
    """
     #Match up the layer with it's source
    def snapsource_lookup(source, sources):
            for k, v in sources.iteritems():
                if v.get("id") == source.get("id"): return k
            return None

    #Set up the proper layer configuration
    def snaplayer_config(layer, sources, user):
        cfg = layer.layer_config(user)
        src_cfg = layer.source_config()
        source = snapsource_lookup(src_cfg, sources)
        if source: cfg["source"] = source
        if src_cfg.get("ptype", "gxp_wmscsource") == "gxp_wmscsource"  or src_cfg.get("ptype", "gxp_gnsource") == "gxp_gnsource" : cfg["buffer"] = 0
        return cfg


    decodedid = num_decode(snapshot)
    snapshot = get_object_or_404(MapSnapshot, pk=decodedid)
    if snapshot.map == map_obj.map:
        config = json.loads(clean_config(snapshot.config))
        layers = [l for l in config["map"]["layers"]]
        sources = config["sources"]
        maplayers = []
        for ordering, layer in enumerate(layers):
            maplayers.append(                             
                layer_from_viewer_config(
                    MapLayer, layer, config["sources"][layer["source"]], ordering))                                              
#             map_obj.map.layer_set.from_viewer_config(
#                 map_obj, layer, config["sources"][layer["source"]], ordering))
        config['map']['layers'] = [snaplayer_config(l,sources,user) for l in maplayers]
    else:
        config = map_obj.viewer_json(user)
    return config


def get_suffix_if_custom(map):
    if map.use_custom_template:
        if map.officialurl:
            return map.officialurl
        elif map.urlsuffix:
            return map.urlsuffix
        else:
            return None
    else:
        return None


def snapshot_create(request):
    """
    Create a permalinked map
    """
    conf = request.body

    if isinstance(conf, basestring):
        config = json.loads(conf)
        snapshot = MapSnapshot.objects.create(config=clean_config(conf),map=Map.objects.get(id=config['id']))
        return HttpResponse(num_encode(snapshot.id), mimetype="text/plain")
    else:
        return HttpResponse("Invalid JSON", mimetype="text/plain", status=500)


def ajax_snapshot_history(request, mapid):
    map_obj = Map.objects.get(pk=mapid)
    history = [snapshot.json() for snapshot in map_obj.snapshots]
    return HttpResponse(json.dumps(history), mimetype="text/plain")


@login_required
def deletemapnow(request, mapid):
    ''' Delete a map, and its constituent layers. '''
    map_obj = get_object_or_404(Map,pk=mapid)

    if not request.user.has_perm('maps.delete_map', obj=map):
        return HttpResponse(render_to_string('401.html',
            RequestContext(request, {'error_message':
                                         _("You are not permitted to delete this map.")})), status=401)

    layers = map_obj.layer_set.all()
    for layer in layers:
        layer.delete()

    snapshots = map_obj.snapshot_set.all()
    for snapshot in snapshots:
        snapshot.delete()
    map_obj.delete()

    return HttpResponseRedirect(request.user.get_profile().get_absolute_url())


def mobilemap(request, mapid=None, snapshot=None):
    if mapid is None:
        return new_map(request)
    else:
        if mapid.isdigit():
            map_obj = Map.objects.get(pk=mapid)
        else:
            map_obj = Map.objects.get(urlsuffix=mapid)

        if not request.user.has_perm('maps.view_map', obj=map_obj):
            return HttpResponse(_("Not Permitted"), status=401, mimetype="text/plain")
        if snapshot is None:
            config = map_obj.viewer_json(request.user)
        else:
            config = snapshot_config(snapshot, map_obj, request.user)

        first_visit_mobile = True
        if request.session.get('visit_mobile' + str(map_obj.id), False):
            first_visit_mobile = False
        else:
            request.session['visit_mobile' + str(map_obj.id)] = True
        config['first_visit_mobile'] = first_visit_mobile
        
    return render_to_response('maps/mobilemap.html', RequestContext(request, {
        'config': json.dumps(config),
        'GOOGLE_API_KEY' : settings.GOOGLE_API_KEY,
        'GEOSERVER_BASE_URL' : ogc_server_settings.public_url,
        'DB_DATASTORE' : ogc_server_settings.DATASTORE,
        'maptitle': map_obj.title,
        'urlsuffix': get_suffix_if_custom(map_obj),
    }))

def embed(request, mapid, snapshot=None):
    if mapid.isdigit():
        map_obj = get_object_or_404(Map,pk=mapid)
    else:
        map_obj = get_object_or_404(Map,urlsuffix=mapid)

    if not request.user.has_perm('maps.view_map', obj=map_obj):
        return HttpResponse(_("Not Permitted"), status=401, mimetype="text/plain")
    if snapshot is None:
        config = map_obj.viewer_json(request.user)
    else:
        config = snapshot_config(snapshot, map_obj, request.user)
    config['first_visit'] = False
        
    return render_to_response('maps/embed.html', RequestContext(request, {
        'config': json.dumps(config)
    }))


def printmap(request, mapid=None, snapshot=None):  
    return render_to_response('maps/map_print.html', RequestContext(request, {}))

def get_suffix_if_custom(map):
    if map.use_custom_template:
        if map.officialurl:
            return map.officialurl
        elif map.urlsuffix:
            return map.urlsuffix
        else:
            return None
    else:
        return None

def official_site(request, site):
    """
    The view that returns the map composer opened to
    the map with the given official site url.
    """
    map_obj = _resolve_map_custom(request, site, 'officialurl', 'maps.view_map', _PERMISSION_MSG_VIEW)
    return map_view(request, str(map_obj.id))

def official_site_mobile(request, site):
    """
    The view that returns the map composer opened to
    the map with the given official site url.
    """
    map_obj = _resolve_map_custom(request, site, 'officialurl', 'maps.view_map', _PERMISSION_MSG_VIEW)
    return mobilemap(request, str(map_obj.id))


def official_site_info(request, site):
    '''
    main view for map resources, dispatches to correct
    view based on method and query args.
    '''
    map_obj = _resolve_map_custom(request, site, 'officialurl', 'maps.view_map', _PERMISSION_MSG_VIEW)
    return map_detail(request, str(map_obj.id))

def tweetview(request):
    map = get_object_or_404(Map,urlsuffix="tweetmap")
    config = map.viewer_json(request.user)

    redirectPage = 'maps/tweetview.html'

    first_visit = True
    if request.session.get('visit' + str(map.id), False):
        first_visit = False
    else:
        request.session['visit' + str(map.id)] = True

    mapstats, created = MapStats.objects.get_or_create(map=map)
    mapstats.visits += 1
    if created or first_visit:
        mapstats.uniques+=1
    mapstats.save()


    #Remember last visited map
    request.session['lastmap'] = map.id
    request.session['lastmapTitle'] = map.title

    config['first_visit'] = first_visit
    config['edit_map'] = request.user.has_perm('maps.change_map', obj=map)

    geops_ip = settings.GEOPS_IP
    if "geopsip" in request.GET:
        geops_ip = request.GET["geopsip"]

    try:
        conn = httplib2.Http(timeout=10)
        testUrl = "http://" +  settings.GEOPS_IP  + "?REQUEST%3DGetFeatureInfo%26SQL%3Dselect%20min(time)%2Cmax(time)%20from%20tweets"
        #testUrl = "http://worldmap.harvard.edu"
        resp, content = conn.request(testUrl, 'GET')
        timerange = json.loads(content)

    except:
        redirectPage = "maps/tweetstartup.html"

    return render_to_response(redirectPage, RequestContext(request, {
        'config': json.dumps(config),
        'GOOGLE_API_KEY' : settings.GOOGLE_API_KEY,
        'GEOSERVER_BASE_URL' : settings.GEOSERVER_BASE_URL,
        'maptitle': map.title,
        'GEOPS_IP': geops_ip,
        'urlsuffix': get_suffix_if_custom(map),
        'tweetdownload': request.user.is_authenticated() and request.user.get_profile().is_org_member,
        'min_date': timerange["results"][0]["min"]*1000,
        'max_date': timerange["results"][0]["max"]*1000
    }))
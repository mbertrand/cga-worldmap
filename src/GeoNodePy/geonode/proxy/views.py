from django.http import HttpResponse
from httplib import HTTPConnection
from urlparse import urlsplit
import httplib2
import urllib
import simplejson
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
import logging
from urlparse import urlparse
from geonode.maps.models import LayerStats, Layer
import re
from django.shortcuts import render_to_response, get_object_or_404


logger = logging.getLogger("geonode.proxy.views")

HGL_URL = 'http://hgl.harvard.edu:8080/HGL'


_user, _password = settings.GEOSERVER_CREDENTIALS
h = httplib2.Http()
h.add_credentials(_user, _password)
_netloc = urlparse(settings.GEOSERVER_BASE_URL).netloc
h.authorizations.append(
    httplib2.BasicAuthentication(
        (_user, _password),
        _netloc,
        settings.GEOSERVER_BASE_URL,
            {},
        None,
        None,
        h
    )
)

@csrf_exempt
def proxy(request):
    if 'url' not in request.GET:
        return HttpResponse(
                "The proxy service requires a URL-encoded URL as a parameter.",
                status=400,
                content_type="text/plain"
                )

    url = urlsplit(request.GET['url'])
    locator = url.path
    if url.query != "":
        locator += '?' + url.query
    if url.fragment != "":
        locator += '#' + url.fragment


    logger.debug("%s: %s : %s : %s", url.hostname, url.port, locator, settings.SESSION_COOKIE_NAME)
    headers = {}
    if settings.SESSION_COOKIE_NAME in request.COOKIES:
        headers["Cookie"] = request.META["HTTP_COOKIE"]

    conn = HTTPConnection(url.hostname, url.port)
    conn.request(request.method, locator, request.raw_post_data, headers)
    result = conn.getresponse()
    response = HttpResponse(
            result.read(),
            status=result.status,
            content_type=result.getheader("Content-Type", "text/plain")
            )
    return response

@csrf_exempt
def geoserver_ows_proxy(request):
    url = settings.GEOSERVER_BASE_URL + "?" + request.GET.urlencode()

    headers = dict()
    if request.method in ("POST", "PUT") and "CONTENT_TYPE" in request.META:
        headers["Content-Type"] = request.META["CONTENT_TYPE"]
         #if "WfsDispatcher" in url:
          #look for typename in XML, <wfs:Query typeName="feature:polytest2a_ifu"....
    elif "REQUEST" in request.GET:
        request_type = request.GET['REQUEST']
        if request_type in ["GetMap","GetFeatureInfo"]:
            type_name = urllib.unquote(request.GET['LAYERS'])
        elif request_type == "GetFeature":
            type_name = request.GET['typeName']
        try:
            layer_obj = Layer.objetcs.get(Layer, type_name=type_name)

            has_permission = request.user.has_perm("maps.change_layer", obj=layer_obj)  if request.method in (
            "POST", "PUT") else request.user.has_perm("maps.view_layer", obj=layer_obj)

            if not has_permission:
                return 401

        except:
            logger.info("Could not find layer %s", type_name)

    http = httplib2.Http()
    http.add_credentials(*settings.GEOSERVER_CREDENTIALS)


    def strip_prefix(path, prefix):
        assert path.startswith(prefix)
        return path[len(prefix):]

    path = strip_prefix(request.get_full_path(),  urlsplit(settings.GEOSERVER_BASE_URL).path)
    url = "".join([settings.GEOSERVER_BASE_URL,  path])

    response, content = http.request(
        url, request.method,
        body=request.raw_post_data or None)

    return HttpResponse(
        content=content,
        status=response.status,
        mimetype=response.get("content-type", "text/plain"))

@csrf_exempt
def geoserver_rest_proxy(request, proxy_path, downstream_path):
    if not request.user.is_authenticated():
        return HttpResponse(
            "You must be logged in to access GeoServer",
            mimetype="text/plain",
            status=401)

    def strip_prefix(path, prefix):
        assert path.startswith(prefix)
        return path[len(prefix):]

    path = strip_prefix(request.get_full_path(), proxy_path)
    url = "".join([settings.GEOSERVER_BASE_URL, downstream_path, path])

    http = httplib2.Http()
    http.add_credentials(*settings.GEOSERVER_CREDENTIALS)
    headers = dict()

    if request.method in ("POST", "PUT") and "CONTENT_TYPE" in request.META:
        headers["Content-Type"] = request.META["CONTENT_TYPE"]

    response, content = http.request(
        url, request.method,
        body=request.raw_post_data or None,
        headers=headers)

    return HttpResponse(
        content=content,
        status=response.status,
        mimetype=response.get("content-type", "text/plain"))


def picasa(request):
    url = "http://picasaweb.google.com/data/feed/base/all?thumbsize=160c&"
    kind = request.GET['kind'] if request.method == 'GET' else request.POST['kind']
    bbox = request.GET['bbox'] if request.method == 'GET' else request.POST['bbox']
    query = request.GET['q'] if request.method == 'GET' else request.POST['q']
    maxResults = request.GET['max-results'] if request.method == 'GET' else request.POST['max-results']
    coords = bbox.split(",")
    coords[0] = -180 if float(coords[0]) <= -180 else coords[0]
    coords[2] = 180 if float(coords[2])  >= 180 else coords[2]
    coords[1] = coords[1] if float(coords[1]) > -90 else -90
    coords[3] = coords[3] if float(coords[3])  < 90 else 90
    newbbox = str(coords[0]) + ',' + str(coords[1]) + ',' + str(coords[2]) + ',' + str(coords[3])
    url = url + "kind=" + kind + "&max-results=" + maxResults + "&bbox=" + newbbox + "&q=" + urllib.quote(query.encode('utf-8'))  #+ "&alt=json"

    feed_response = urllib.urlopen(url).read()
    return HttpResponse(feed_response, mimetype="text/xml")

def hglpoints (request):
    from xml.dom import minidom
    import re
    url = HGL_URL + "/HGLGeoRSS?GeometryType=point"
    bbox = ["-180","-90","180","90"]
    max_results = request.GET['max-results'] if request.method == 'GET' else request.POST['max-results']
    if max_results is None:
        max_results = "100"
    try:
        bbox = request.GET['bbox'].split(",") if request.method == 'GET' else request.POST['bbox'].split(",")
    except:
        pass
    query = request.GET['q'] if request.method == 'GET' else request.POST['q']
    url = url + "&UserQuery=" + urllib.quote(query.encode('utf-8')) #+ \
        #"&BBSearchOption=1&minx=" + bbox[0] + "&miny=" + bbox[1] + "&maxx=" + bbox[2] + "&maxy=" + bbox[3]
    dom = minidom.parse(urllib.urlopen(url))
    iterator = 1
    for node in dom.getElementsByTagName('item'):
        if iterator <= int(max_results):
            description = node.getElementsByTagName('description')[0]
            guid = node.getElementsByTagName('guid')[0]
            title = node.getElementsByTagName('title')[0]
            if guid.firstChild.data != 'OWNER.TABLE_NAME':
                description.firstChild.data = description.firstChild.data + '<br/><br/><p><a href=\'javascript:void(0);\' onClick=\'app.addHGL("' \
                    + escape(title.firstChild.data) + '","' + re.sub("SDE\d?\.","", guid.firstChild.data)  + '");\'>Add to Map</a></p>'
            iterator +=1
        else:
            node.parentNode.removeChild(node)

    return HttpResponse(dom.toxml(), mimetype="text/xml")


def hglServiceStarter (request, layer):
    #Check if the layer is accessible to public, if not return 403
    accessUrl = HGL_URL + "/ogpHglLayerInfo.jsp?ValidationKey=" + settings.HGL_VALIDATION_KEY +"&layers=" + layer
    accessJSON = simplejson.loads(urllib.urlopen(accessUrl).read())
    if accessJSON[layer]['access'] == 'R':
        return HttpResponse(status=403)

    #Call the RemoteServiceStarter to load the layer into HGL's Geoserver in case it's not already there
    startUrl = HGL_URL + "/RemoteServiceStarter?ValidationKey=" + settings.HGL_VALIDATION_KEY + "&AddLayer=" + layer
    return HttpResponse(urllib.urlopen(startUrl).read())




def youtube(request):
    url = "http://gdata.youtube.com/feeds/api/videos?v=2&prettyprint=true&"
    bbox = request.GET['bbox'] if request.method == 'GET' else request.POST['bbox']
    query = request.GET['q'] if request.method == 'GET' else request.POST['q']
    maxResults = request.GET['max-results'] if request.method == 'GET' else request.POST['max-results']
    coords = bbox.split(",")
    coords[0] = coords[0] if float(coords[0]) > -180 else -180
    coords[2] = coords[2] if float(coords[2])  < 180 else 180
    coords[1] = coords[1] if float(coords[1]) > -90 else -90
    coords[3] = coords[3] if float(coords[3])  < 90 else 90
    #location would be the center of the map.
    location = str((float(coords[3]) + float(coords[1]))/2)  + "," + str((float(coords[2]) + float(coords[0]))/2);

    #calculating the location-readius
    R = 6378.1370;
    PI = 3.1415926;
    left = R*float(coords[0])/180.0/PI;
    right = R*float(coords[2])/180.0/PI;
    radius = (right - left)/2*2;
    radius = 1000 if (radius > 1000) else radius;
    url = url + "location=" + location + "&max-results=" + maxResults + "&location-radius=" + str(radius) + "km&q=" + urllib.quote(query.encode('utf-8'))

    feed_response = urllib.urlopen(url).read()
    return HttpResponse(feed_response, mimetype="text/xml")

def download(request, service, layer, format):
    params = request.GET
    #mimetype = params.get("outputFormat") if service == "wfs" else params.get("format")

    service=service.replace("_","/")
    url = settings.GEOSERVER_BASE_URL + service + "?" + params.urlencode()

    layerObj = Layer.objects.get(pk=layer)

    if layerObj.downloadable and request.user.has_perm('maps.view_layer', obj=layerObj):

        layerstats,created = LayerStats.objects.get_or_create(layer=layer)
        layerstats.downloads += 1
        layerstats.save()

        download_response, content = h.request(
            url, request.method,
            body=None,
            headers=dict())
        content_disposition = None
        if 'content_disposition' in download_response:
            content_disposition = download_response['content-disposition']
        mimetype = download_response['content-type']
        response = HttpResponse(content, mimetype = mimetype)
        if content_disposition is not None:
            response['Content-Disposition'] = content_disposition
        else:
            response['Content-Disposition'] = "attachment; filename=" + layerObj.name + "." + format
        return response
    else:
        return HttpResponse(status=403)


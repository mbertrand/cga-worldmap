# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2012 OpenPlans
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################
from django.conf.urls import patterns, url, include

urlpatterns = patterns('geonode.worldmap.proxy.views',
    (r'^proxy/', 'proxy'),
    (r'^gs/rest/styles', 'geoserver_rest_proxy', dict(
        proxy_path='/gs/rest/styles', downstream_path='rest/styles')),
    (r'^gs/rest/layers', 'geoserver_rest_proxy', dict(
        proxy_path='/gs/rest/layers', downstream_path='rest/layers')),
    (r'^gs/rest/sldservice', 'geoserver_rest_proxy', dict(
        proxy_path='/gs/rest/sldservice', downstream_path='rest/sldservice')),
    (r'^picasa/','picasa'),
    (r'^youtube/','youtube'),
    (r'^flickr/','flickr'),
    (r'^hglpoint/','hglpoints'),
    (r'^hglServiceStarter/(?P<layer>[^/]*)/?','hglServiceStarter'),
    (r'^tweettrends','tweetTrendProxy'),
    (r'^tweetserver/(?P<geopsip>[A-Za-z0-9\._\-\:]+)/','tweetServerProxy'),
    (r'^tweetDownload','tweetDownload'),
    (r'^download/(?P<service>[^/]*)/?$','download'),
    (r'', include('geonode.proxy.urls')),
)

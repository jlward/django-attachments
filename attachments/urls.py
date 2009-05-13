from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('attachment.views',
    url(r'^(?P<content_type>\d+)/(?P<object_id>\d+)/$',
        'list_attachments',
        name='attachment_list'),
    url(r'^(?P<content_type>\d+)/(?P<object_id>\d+)/new/$',
        'new_attachment',
        name='attachment_new'),
    url(r'^(?P<attachment_slug>[-\w]+)/delete/$',
        'views.delete_attachment',
        name='attachment_delete'),
)
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core import serializers

from attachments.models import Attachment
from attachments.forms import AttachmentForm


@login_required
def new_attachment(request, content_type, object_id,
                   template_name='attachments/new_attachment.html',
                   form_cls=AttachmentForm):
    object_type = get_object_or_404(ContentType, id = int(content_type))
    try:
        object = object_type.get_object_for_this_type(pk=int(object_id))
    except object_type.DoesNotExist:
        raise Http404
    if request.method == "POST":
        attachment_form = form_cls(request.POST, request.FILES)
        if attachment_form.is_valid():
            attachment = attachment_form.save(commit=False)
            attachment.content_type = object_type
            attachment.object_id = object_id
            attachment.attached_by = request.user
            attachment.save()
            return HttpResponseRedirect(object.get_absolute_url())
    else:
        attachment_form = form_cls()

    return render_to_response(template_name, {
        "attachment_form": attachment_form,
        "object": object
    }, context_instance=RequestContext(request))

@login_required
def delete_attachment(request, attachment_slug):
    attachment = get_object_or_404(Attachment, slug=attachment_slug)
    object_type = attachment.content_type
    try:
        object = object_type.get_object_for_this_type(pk=attachment.object_id)
    except object_type.DoesNotExist:
        raise Http404
    if request.method == "POST":
        attachment.delete()
    return HttpResponseRedirect(object.get_absolute_url())

@login_required
def list_attachments(request, content_type, object_id,
                   template_name='attachments/list_attachments.html'):
    object_type = get_object_or_404(ContentType, id = int(content_type))
    try:
        object = object_type.get_object_for_this_type(pk=int(object_id))
    except object_type.DoesNotExist:
        raise Http404

    attachments = Attachment.objects.attachments_for_object(object)
    if request.META.get('HTTP_ACCEPT', None) == 'application/javascript':
            data = serializers.serialize('json', attachments)
            return HttpResponse(data, mimetype='application/javascript')
    else:
        return render_to_response(template_name, {
            'object_list': attachments,
            'object': object
        }, context_instance=RequestContext(request))



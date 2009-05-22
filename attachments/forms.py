from django import forms
from django.contrib.contenttypes.models import ContentType

from attachments.models import Attachment


class AttachmentForm(forms.ModelForm):

    def save(self, content_object, *args, **kwargs):
        self.instance.content_type = ContentType.objects.get_for_model(
            content_object)
        self.instance.object_id = content_object.pk
        super(AttachmentForm, self).save(*args, **kwargs)

    class Meta:
        model = Attachment
        exclude = ('content_type', 'object_id', 'attached_by')

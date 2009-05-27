from django import forms
from django.contrib.contenttypes.models import ContentType

from attachments.models import Attachment


class AttachmentForm(forms.ModelForm):

    def save(self, content_object=None, *args, **kwargs):
        if content_object:
            self.instance.content_type = ContentType.objects.get_for_model(
                content_object)
            self.instance.object_id = content_object.pk
        elif not self.instance.pk:
            # If we're creating a new attachment, content_object is required
            raise AttributeError, "AttachmentForm.save() requires a content_object for new attachments"

        super(AttachmentForm, self).save(*args, **kwargs)

    def clean(self, cleaned_data):
        """
        Don't delete the old file if our edit doesn't upload a new one.
        """
        if self.instance.pk:
            if not cleaned_data['file']:
                cleaned_data['file'] = self.instance.file

        return cleaned_data

    class Meta:
        model = Attachment
        exclude = ('content_type', 'object_id', 'attached_by')

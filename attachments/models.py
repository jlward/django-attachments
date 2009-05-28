from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import encoding
from django.utils.http import urlquote
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ImproperlyConfigured

import os.path
from datetime import datetime

import directory_schemes
from utils import get_callable_from_string, unique_slugify

# Get relative media path
try:
    ATTACHMENT_DIR = settings.ATTACHMENT_DIR
except:
    ATTACHMENT_DIR = "attachments"

class AttachmentManager(models.Manager):
    """
    Methods borrowed from django-threadedcomments
    """

    def _generate_object_kwarg_dict(self, content_object, **kwargs):
        """
        Generates the most comment keyword arguments for a given ``content_object``.
        """
        kwargs['content_type'] = ContentType.objects.get_for_model(content_object)
        try:
            kwargs['object_id'] = content_object.pk
        except AttributeError:
            kwargs['object_id'] = content_object.id
        return kwargs

    def create_for_object(self, content_object, **kwargs):
        """
        A simple wrapper around ``create`` for a given ``content_object``.
        """
        return self.create(**self._generate_object_kwarg_dict(content_object, **kwargs))

    def attachments_for_object(self, content_object, file_name=None, title=None, **kwargs):
        """
        Prepopulates a QuerySet with all attachments related to the given ``content_object``.
        """
        query = self.filter(**self._generate_object_kwarg_dict(content_object, **kwargs))
        if file_name:
            query = query.filter(file__iendswith=file_name)
        if title:
            query = query.filter(title=title)

        return query

    def copy_attachments(self, from_object, to_object, deepcopy=False):
        """
        Copy all of the attachments on from_object to to_object. The
        fields will be pointing at the same file unless deepcopy is False.
        """
        # First delete all of the attachments on the to_object
        old_attachments = self.attachments_for_object(to_object)
        old_attachments.delete()

        attachments = self.attachments_for_object(from_object)

        for attachment in attachments:
            copy = attachment.copy(to_object, deepcopy)


class Attachment(models.Model):
    def get_attachment_dir(instance, filename):
        """
        The attachment directory to store the file in.

        Builds the location based on the ATTACHMENT_STORAGE_DIR setting which
        is a callable (in the same string format as TEMPLATE_LOADERS) that takes
        an attachment and a filename and then returns a string.
        """
        if getattr(settings, 'ATTACHMENT_STORAGE_DIR', None):
            try:
                dir_builder = get_callable_from_string(
                    settings.ATTACHMENT_STORAGE_DIR)
            except ImproperlyConfigured:
                # Callable didn't load correctly
                dir_builder = directory_schemes.by_app
        else:
            dir_builder = directory_schemes.by_app

        return dir_builder(instance, filename)

    file = models.FileField(_("file"), upload_to=get_attachment_dir,
                            max_length=255)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey("content_type", "object_id")
    attached_timestamp = models.DateTimeField(_("date attached"),
                                              default=datetime.now)
    title = models.CharField(_("title"), max_length=200, blank=True, null=True)
    slug = models.SlugField(_("slug"), editable=False)
    summary = models.TextField(_("summary"), blank=True, null=True)
    attached_by = models.ForeignKey(
        User, verbose_name=_("attached by"),
        related_name="attachment_attached_by", editable=False)

    objects = AttachmentManager()

    class Meta:
        ordering = ['-attached_timestamp']
        get_latest_by = 'attached_timestamp'
        verbose_name = _('attachment')
        verbose_name_plural = _('attachments')

    def __unicode__(self):
        return self.title or self.file_name()

    def save(self, force_insert=False, force_update=False):
        # Ensure this slug is unique amongst attachments attached to this object
        queryset = Attachment.objects.filter(
            content_type=self.content_type, object_id=self.object_id)
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        unique_slugify(self, self.title, queryset=queryset)
        if not self.title:
            self.title = self.file_name()
        super(Attachment, self).save(force_insert, force_update)

    def file_url(self):
        return encoding.iri_to_uri(self.file.url)

    def file_name(self):
        """
        Outputs just the file's name and extension without the full path.
        """
        return os.path.basename(self.file.name)

    def copy(self, to_object, deepcopy=False):
        """
        Create a copy of this attachment that's attached to to_object instead of
        the current content_object. If deepcopy is set to true, the file will be
        copied instead of both attachments pointing at the same file.

        Convoluted copying is needed in order for the upload_to function in the
        FileField to actually be evaluated properly.
        """
        copy = Attachment()

        copy.title = self.title
        copy.slug = self.slug
        copy.summary = self.summary
        copy.attached_by = self.attached_by

        # Modify the generic FK so that it points to the 'to_object'
        kwargs_dict = Attachment.objects._generate_object_kwarg_dict(to_object)
        for field, value in kwargs_dict.items():
            setattr(copy, field, value)

        if deepcopy and self.file:
            copy.file.save(self.file_name(), self.file)
        elif self.file:
            copy.file = file

        copy.save()
        return copy

class TestModel(models.Model):
    """
    This model is simply used by this application's test suite as a model to
    which to attach files.
    """
    name = models.CharField(max_length=32)
    date = models.DateTimeField(default=datetime.now)

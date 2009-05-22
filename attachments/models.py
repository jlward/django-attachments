from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
from django.conf import settings
from django.template.defaultfilters import slugify
from django.utils import encoding
from django.utils.http import urlquote
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ImproperlyConfigured

import re, os.path

from datetime import datetime

import directory_schemes

# Get relative media path
try:
    ATTACHMENT_DIR = settings.ATTACHMENT_DIR
except:
    ATTACHMENT_DIR = "attachments"


def unique_slugify(instance, value, slug_field_name='slug', queryset=None,
                   slug_separator='-'):
    """
    Calculates a unique slug of ``value`` for an instance.

    ``slug_field_name`` should be a string matching the name of the field to
    store the slug in (and the field to check against for uniqueness).

    ``queryset`` usually doesn't need to be explicitly provided - it'll default
    to using the ``.all()`` queryset from the model's default manager.

    from http://www.djangosnippets.org/snippets/690/
    """

    slug_field = instance._meta.get_field(slug_field_name)

    slug = getattr(instance, slug_field.attname)
    slug_len = slug_field.max_length

    # Sort out the initial slug. Chop its length down if we need to.
    slug = slugify(value)
    if slug_len:
        slug = slug[:slug_len]
    slug = _slug_strip(slug, slug_separator)
    original_slug = slug

    # Create a queryset, excluding the current instance.
    if not queryset:
        queryset = instance.__class__._default_manager.all()
        if instance.pk:
            queryset = queryset.exclude(pk=instance.pk)

    # Find a unique slug. If one matches, at '-2' to the end and try again
    # (then '-3', etc).
    next = 2
    while not slug or queryset.filter(**{slug_field_name: slug}):
        slug = original_slug
        end = '-%s' % next
        if slug_len and len(slug) + len(end) > slug_len:
            slug = slug[:slug_len-len(end)]
            slug = _slug_strip(slug, slug_separator)
        slug = '%s%s' % (slug, end)
        next += 1

    setattr(instance, slug_field.attname, slug)


def _slug_strip(value, separator=None):
    """
    Cleans up a slug by removing slug separator characters that occur at the
    beginning or end of a slug.

    If an alternate separator is used, it will also replace any instances of
    the default '-' separator with the new separator.
    """
    if separator == '-' or not separator:
        re_sep = '-'
    else:
        re_sep = '(?:-|%s)' % re.escape(separator)
        value = re.sub('%s+' % re_sep, separator, value)
    return re.sub(r'^%s+|%s+$' % (re_sep, re_sep), '', value)


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

    def attachments_for_object(self, content_object, **kwargs):
        """
        Prepopulates a QuerySet with all attachments related to the given ``content_object``.
        """
        return self.filter(**self._generate_object_kwarg_dict(content_object, **kwargs))

    def shallow_copy_attachments(self, from_object, to_object):
        """
        Shallowly copy all of the attachments on from_object to to_object. The
        fields will be pointing at the same file.
        """
        # First delete all of the attachments on the to_object
        old_attachments = self.attachments_for_object(to_object)
        old_attachments.delete()

        attachments = self.attachments_for_object(from_object)

        for attachment in attachments:
            copy = attachment
            # Copy over all of the field values
            #for field_name in attachment._meta.get_all_field_names():
            #    setattr(copy, field_name, getattr(attachment, field_name))

            # Modify the generic FK so that it points to the 'to_object'
            kwargs_dict = self._generate_object_kwarg_dict(to_object)
            for field, value in kwargs_dict.items():
                setattr(copy, field, value)

            # Clear the PK so that we're creating another
            copy.pk = None
            copy.save()

    def deep_copy_attachments(self, from_object, to_object):
        """
        Deeply copy all of the attachments on from_object to to_object. The
        file is duplicated also.
        """
        # First delete all of the attachments on the to_object
        old_attachments = self.attachments_for_object(to_object)
        old_attachments.delete()

        attachments = self.attachments_for_object(from_object)

        for attachment in attachments:
            copy = attachment

            # Modify the generic FK so that it points to the 'to_object'
            kwargs_dict = self._generate_object_kwarg_dict(to_object)
            for field, value in kwargs_dict.items():
                setattr(copy, field, value)

            # Clear the PK so that we're creating another
            copy.pk = None
            copy.save()

def get_callable_from_string(path):
    """
    Gets a callable from a string representing an import
    (eg. django.template.loaders.filesystem.load_template_source).
    Adapted from django.template.loader.find_template_source
    """
    i = path.rfind('.')
    module, attr = path[:i], path[i+1:]
    try:
        mod = __import__(module, globals(), locals(), [attr])
    except ImportError, e:
        raise ImproperlyConfigured, 'Error importing callable %s: "%s"' % (module, e)
    try:
        func = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured, 'Module "%s" does not define a "%s" callable' % (module, attr)

    return func

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
        unique_slugify(self, self.title)
        super(Attachment, self).save(force_insert, force_update)

    def file_url(self):
        return encoding.iri_to_uri(self.file.url)

    def file_name(self):
        """
        Outputs just the file's name and extension without the full path.
        """
        return os.path.basename(self.file.name)

class TestModel(models.Model):
    """
    This model is simply used by this application's test suite as a model to
    which to attach files.
    """
    name = models.CharField(max_length=32)
    date = models.DateTimeField(default=datetime.now)

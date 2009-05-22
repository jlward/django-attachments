import os.path

def site_based(attachment, filename):
    return os.path.join('foo', filename)

def by_app(attachment, filename):
    """
    Default for barTC's scheme on github. Thanks bartTC
    """
    return 'attachments/%s/%s/%s' % (
            '%s_%s' % (attachment.content_object._meta.app_label,
                       attachment.content_object._meta.object_name.lower()),
                       attachment.content_object.pk,
                       filename)
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files import File

from attachments.models import Attachment, TestModel

import os
from tempfile import NamedTemporaryFile

"""

>>> from attachments.models import Attachment, TestModel
>>> from django.contrib.auth.models import User
>>> from django.contrib.contenttypes.models import ContentType

>>> import os
>>> TEST_DIR = os.path.join(os.path.dirname(__file__))
>>> TEST_FILE1 = os.path.join(TEST_DIR, "models.py")
>>> TEST_FILE2 = os.path.join(TEST_DIR, "views.py")

>>> bob = User(username="bob")
>>> bob
<User: bob>
>>> bob.save()

>>> tm = TestModel(name="Test1")
>>> tm.name
'Test1'
>>> tm.save()


>>> att1 = Attachment.objects.create_for_object(
...     tm, file=TEST_FILE1, attached_by=bob, title="Something",
...     summary="Something more")
>>> att1
<Attachment: Something>


>>> att2 = Attachment.objects.create_for_object(
...     tm, file=TEST_FILE2, attached_by=bob, title="Something Else",
...     summary="Something else more")
>>> att2
<Attachment: Something Else>

>>> Attachment.objects.attachments_for_object(tm)
[<Attachment: Something Else>, <Attachment: Something>]
"""

class TestAttachmentCopying(TestCase):
    def setUp(self):
        self.client = Client(REMOTE_ADDR='localhost')
        self.bob = User(username="bob")
        self.bob.save()

        self.tm = TestModel(name="Test1")
        self.tm.save()
        self.tm2 = TestModel(name="Test2")
        self.tm2.save()

        self.test_file1 = NamedTemporaryFile('w+')
        self.test_file1.write("some test text")
        self.test_file1.flush()
        self.test_file1.seek(0)

        self.test_file2 = NamedTemporaryFile('w+')
        self.test_file2.write("some test text")
        self.test_file2.flush()
        self.test_file2.seek(0)

    def testDeepCopying(self):
        """
        Test that doing a deep copy of a file actually attempt to create a
        second version of a file.
        """
        att1 = Attachment.objects.create_for_object(
            self.tm, file=self.test_file1, attached_by=self.bob,
            title="Something", summary="Something")
        f = File(self.test_file1)
        att1.file.save('models.py', f)

        att2 = att1.copy(self.tm2, deepcopy=True)

        # Ensure the saved_copy uses its proper file path
        attachments = Attachment.objects.attachments_for_object(self.tm2)
        for attachment in attachments:
            self.assertEqual(
                attachment.file.name,
                Attachment.get_attachment_dir(attachment,
                                              attachment.file_name())
            )
from django.test import TestCase

from django_delayed_union import DelayedUnionQuerySet
from django_delayed_union.base import DelayedQuerySetBase
from django_delayed_union.base import DelayedQuerySetDescriptor


class DelayedQuerySetBaseTests(TestCase):
    def setUp(self):
        super(DelayedQuerySetBaseTests, self).setUp()
        self.cls = DelayedUnionQuerySet

    def test_has_metaclass(self):
        self.assertTrue(
            issubclass(type(self.cls), DelayedQuerySetBase)
        )

    def test_descriptors_have_names_set(self):
        for name in dir(self.cls):
            descriptor = getattr(self.cls, name)
            if not isinstance(descriptor, DelayedQuerySetDescriptor):
                continue
            self.assertEqual(descriptor.name, name)

from django_delayed_union.base import DelayedQuerySetDescriptor
from sphinx.ext.autodoc import AttributeDocumenter
from sphinx.ext.autodoc import DocstringSignatureMixin


class DelayedQuerySetDescriptorDocumenter(AttributeDocumenter):
    objtype = 'delayedquerysetdescriptor'
    directivetype = 'attribute'
    priority = AttributeDocumenter.priority + 1

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, DelayedQuerySetDescriptor)

    def format_signature(self):
        return DocstringSignatureMixin.format_signature(self)


def setup(app):
    app.add_autodocumenter(DelayedQuerySetDescriptorDocumenter)
    return {'version': '0.1'}   # identifies the version of our extension

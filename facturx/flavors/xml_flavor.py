"""
This module abstracts different XML flavors used to represent the underlying invoice data.

Data kept for each flavor:

- mapping between "pivot" dict and XML paths
- xmp templates
- xsd files for validation
- xml templates to create new XML representations
"""

import os
from lxml import etree

import pycountry
import yaml

from ..logger import logger

unicode = str


# Load information on different XML standards and paths from YML.
def _load_yml(filename):
    with open(os.path.join(os.path.dirname(__file__), filename)) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


FIELDS = _load_yml('fields.yml')
FLAVORS = _load_yml('flavors.yml')


class XMLFlavor(object):
    """A helper class to keep the lookup code out of the main library.

    Represents a XML invoice representation standard, like Factur-X.
    """

    def __init__(self, xml):
        self.name = guess_flavor(xml)
        self.level = self.get_level(xml)
        self.details = FLAVORS[self.name]

    @classmethod
    def from_template(cls, flavor, level):
        """Creates a new XML tree with the desired level and flavor from an existing template

        Returns lxml.etree and xml_flavor.XMLFlavor instance.
        """
        template_filename = os.path.join(
            os.path.dirname(__file__),
            flavor,
            'xml',
            FLAVORS[flavor]['levels'][level]['xml'])
        assert os.path.isfile(template_filename), 'Template for this flavor/level does not exist.'
        parser = etree.XMLParser(remove_blank_text=True)
        xml_tree = etree.parse(open(template_filename), parser).getroot()
        return cls(xml_tree), xml_tree

    def get_level(self, facturx_xml_etree):
        if not isinstance(facturx_xml_etree, type(etree.Element('pouet'))):
            raise ValueError('facturx_xml_etree must be an etree.Element() object')
        namespaces = facturx_xml_etree.nsmap
        doc_id_xpath = facturx_xml_etree.xpath(self.get_xml_path('version'), namespaces=namespaces)
        if not doc_id_xpath:
            raise ValueError("Version field not found.")
        doc_id = doc_id_xpath[0].text
        level = doc_id.split(':')[-1]
        if level not in FLAVORS[self.name]['levels']:
            level = doc_id.split(':')[-2]
        if level not in FLAVORS[self.name]['levels']:
            raise ValueError(
                "Invalid Factur-X URN: '%s'" % doc_id)

        return level

    def check_xsd(self, etree_to_validate):
        """Validate the XML file against the XSD"""

        xsd_filename = FLAVORS[self.name]['levels'][self.level]['schema']
        xsd_file = os.path.join(
            os.path.dirname(__file__),
            self.name, 'xsd', xsd_filename)

        xsd_etree_obj = etree.parse(open(xsd_file))
        official_schema = etree.XMLSchema(xsd_etree_obj)
        try:
            official_schema.assertValid(etree_to_validate)
        except Exception as e:
            # if the validation of the XSD fails, we arrive here
            logger.warning(
                "The XML file is invalid against the XML Schema Definition")
            logger.warning('XSD Error: %s', e)
            raise Exception(
                "The %s XML file is not valid against the official "
                "XML Schema Definition. "
                "Here is the error, which may give you an idea on the "
                "cause of the problem: %s." % (self.name, unicode(e)))
        return True

    def get_xmp_xml(self):
        xmp_file = os.path.join(
            os.path.dirname(__file__),
            self.name,
            'xmp',
            FLAVORS[self.name]['xmp_schema'])
        return etree.parse(open(xmp_file))

    def get_xml_path(self, field_name):
        """Return XML path based on field_name and flavor"""

        assert field_name in FIELDS.keys(), 'Field not specified. Try working directly on the XML tree.'
        field_details = FIELDS[field_name]
        if self.name in field_details['_path']:
            return field_details['_path'][self.name]
        else:
            raise KeyError('Path not defined for currenct flavor.')

    def valid_code(self, code_type, field_value):
        try:
            if code_type == 'country':
                pycountry.countries.lookup(field_value)
            elif code_type == 'currency':
                pycountry.currencies.lookup(field_value)
            return True
        except LookupError:
            return False


def valid_xmp_filenames():
    result = []
    for flavor in FLAVORS.keys():
        result.append(FLAVORS[flavor]['xmp_filename'])
    return result


def guess_flavor(facturx_xml_etree):
    if not isinstance(facturx_xml_etree, type(etree.Element('pouet'))):
        raise ValueError('facturx_xml_etree must be an etree.Element() object')
    if facturx_xml_etree.tag.startswith('{urn:un:unece:uncefact:'):
        flavor = 'factur-x'
    else:
        raise Exception(
            "Could not detect if the invoice is a Factur-X"
            "invoice.")
    return flavor

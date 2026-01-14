import copy
import io
import json
import os
from datetime import datetime
from io import BytesIO

import yaml
from .constants import EN16931
from lxml import etree
from pypdf import PdfReader
from pypdf.generic import IndirectObject

from .flavors import xml_flavor
from .logger import logger
from .pdfwriter import FacturXPDFWriter

file_types = (io.IOBase,)
unicode = str

__all__ = ['FacturX']

class FacturX(object):
    """Represents an electronic PDF invoice with embedded XML metadata following the
    Factur-X standard.

    The source of truth is always the underlying XML tree. No copy of field
    data is kept. Manipulation of the XML tree is either done via Python-style
    dict access (available for the most common fields) or by directly accessing
    the XML data on `FacturX.xml`.

    Attributes:
    - xml: xml tree of machine-readable representation.
    - pdf: underlying graphical PDF representation.
    - flavor: which flavor (Factur-x) to use.
    """

    def __init__(self, pdf_invoice, flavor='factur-x', level='minimum'):
        # Read PDF from path, pointer or string
        if isinstance(pdf_invoice, str) and os.path.isfile(pdf_invoice):
            with open(pdf_invoice, 'rb') as f:
                pdf_file = BytesIO(f.read())
        elif isinstance(pdf_invoice, file_types):
            pdf_file = pdf_invoice
        else:
            raise TypeError(
                "The first argument of the method get_facturx_xml_from_pdf must "
                "be either a string or a file (it is a %s)." % type(pdf_invoice))
        xml = self._xml_from_file(pdf_file)
        self.pdf = pdf_file

        # PDF has metadata embedded
        if xml is not None:
            # 'Read existing XML from PDF
            self.xml = xml
            self.flavor = xml_flavor.XMLFlavor(xml)
        else:
            # No metadata embedded. Create from template.
            # 'PDF does not have XML embedded. Adding from template.'
            self.flavor, self.xml = xml_flavor.XMLFlavor.from_template(flavor, level)

        self.flavor.check_xsd(self.xml)
        self._namespaces = self.xml.nsmap

        self.already_added_field = {}

    def read_xml(self):
        """Use XML data from external file. Replaces existing XML or template."""
        pass

    def _xml_from_file(self, pdf_file):
        pdf = PdfReader(pdf_file)
        pdf_root = pdf.trailer['/Root']
        if '/Names' not in pdf_root or '/EmbeddedFiles' not in pdf_root['/Names']:
            # 'No existing XML file found.'
            return None

        for file in pdf_root['/Names']['/EmbeddedFiles']['/Names']:
            if isinstance(file, IndirectObject):
                obj = file.get_object()
                if obj['/F'] in xml_flavor.valid_xmp_filenames():
                    xml_root = etree.fromstring(obj['/EF']['/F'].get_data())
                    xml_content = xml_root

                    return xml_content

    def __getitem__(self, field_name):
        path = self.flavor.get_xml_path(field_name)
        value = self.xml.xpath(path, namespaces=self._namespaces)
        if value:
            value = value[0].text
        if 'date' in field_name and value:
            value = datetime.strptime(value, '%Y%m%d')
        return value

    def __setitem__(self, field_name, value):
        path = self.flavor.get_xml_path(field_name)
        res = self.xml.xpath(path, namespaces=self._namespaces)
        if not res:
            # The node is not defined at all in the parsed xml
            # logger.warning("{} is not defined in {}".format(path, self.flavor.name))
            return

        current_el = res[-1]
        parent_tag = current_el.getparent().tag

        self._handle_duplicated_node(current_el, parent_tag)
        self._write_element(current_el, field_name, value)
        self._save_to_registry(current_el, parent_tag)

    def _handle_duplicated_node(self, current_el, parent_tag):
        # method meant to handle cardinality 1.n (ApplicableTradeTax or IncludedSupplyChainTradeLineItem)
        # we get the sibling and duplicate it
        if parent_tag in self.already_added_field and current_el in self.already_added_field[parent_tag]:
            parent_el = current_el.getparent()
            parent_el.addnext(copy.copy(parent_el))

    def _write_element(self, current_el, field_name, value):
        # if we have type cast worries, it must be handled here
        if 'date' in field_name:
            assert isinstance(value, datetime), 'Please pass date values as DateTime() object.'
            value = value.strftime('%Y%m%d')
            current_el.attrib['format'] = '102'
            current_el.text = value
        # if en16931 temporary, will eventually be removed once sure its applicable to basicwl too
        elif self.flavor.level == EN16931 and field_name == 'seller_email' and ':' in value:
            current_el.text = str(value.split(':')[1])
            current_el.attrib['schemeID'] = str(value.split(':')[0])
        else:
            current_el.text = str(value)

    def _save_to_registry(self, current_el, parent_tag):
        if parent_tag not in self.already_added_field:
            self.already_added_field[parent_tag] = [current_el]
        elif current_el not in self.already_added_field[parent_tag]:
            self.already_added_field[parent_tag].append(current_el)

    def is_valid(self):
        """Make every effort to validate the current XML.

        Checks:
        - all required fields are present and have values.
        - XML is valid
        - ...

        Returns: true/false (validation passed/failed)
        """
        # validate against XSD
        try:
            self.flavor.check_xsd(self.xml)
        except Exception:
            return False

        # Check for required fields
        fields_data = xml_flavor.FIELDS
        for field in fields_data.keys():
            if fields_data[field]['_required']:
                r = self.xml.xpath(fields_data[field]['_path'][self.flavor.name], namespaces=self._namespaces)
                if not len(r) or r[0].text is None:
                    if '_default' in fields_data[field].keys():
                        self[field] = fields_data[field]['_default']
                    else:
                        logger.warning("Required field '%s' is not present", field)
                        return False

        # Check for codes (ISO:3166, ISO:4217)
        codes_to_check = [
            ('currency', 'currency'),
            ('country', 'seller_country'),
            ('country', 'buyer_country'),
            ('country', 'shipping_country')
        ]
        for code_type, field_name in codes_to_check:
            if self[field_name] and not self.flavor.valid_code(code_type, self[field_name]):
                logger.warning("Field %s is not a valid %s code." % (field_name, code_type))
                return False

        return True

    def write_pdf(self, path):
        pdfwriter = FacturXPDFWriter(self)
        with open(path, 'wb') as output_f:
            pdfwriter.write(output_f)
        return True

    @property
    def xml_str(self):
        """Calculate MD5 checksum of XML file. Used for PDF attachment."""
        return etree.tostring(self.xml, pretty_print=True)

    def write_xml(self, path):
        with open(path, 'wb') as f:
            f.write(self.xml_str)

    def to_dict(self):
        """Get all available fields as dict."""
        fields_data = xml_flavor.FIELDS
        flavor = self.flavor.name

        output_dict = {}
        for field in fields_data.keys():
            try:
                if fields_data[field]['_path'][flavor] is not None:
                    r = self.xml.xpath(fields_data[field]['_path'][flavor],
                                       namespaces=self._namespaces)
                    output_dict[field] = r[0].text
            except IndexError:
                output_dict[field] = None

        return output_dict

    def write_json(self, json_file_path='output.json'):
        json_output = self.to_dict()
        if self.is_valid():
            with open(json_file_path, 'w') as json_file:
                logger.info("Exporting JSON to %s", json_file_path)
                json.dump(json_output, json_file, indent=4, sort_keys=True)

    def write_yaml(self, yml_file_path='output.yml'):
        yml_output = self.to_dict()
        if self.is_valid():
            with open(yml_file_path, 'w') as yml_file:
                logger.info("Exporting YAML to %s", yml_file_path)
                yaml.dump(yml_output, yml_file, default_flow_style=False)

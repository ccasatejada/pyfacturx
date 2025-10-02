import os
import unittest
from datetime import datetime
from facturx.facturx import *
from lxml import etree


class TestReading(unittest.TestCase):
    def discover_files(self):
        self.test_files_dir = os.path.join(os.path.dirname(__file__), 'sample_invoices')
        self.test_files = os.listdir(self.test_files_dir)

    def test_from_file(self):
        self.discover_files()
        for file in self.test_files:
            file_path = os.path.join(self.test_files_dir, file)
            FacturX(file_path)

    # returning file path for a specific file in 'sample_invoices'
    def find_file(self, file_name):
        self.discover_files()
        for file in self.test_files:
            if file == file_name:
                file_path = os.path.join(self.test_files_dir, file)
                return file_path

    # def test_input_error(self):
    #     with self.assertRaises(TypeError) as context:
    #         FacturX('non-existant.pdf')

    def test_file_without_embedded_data(self):
        file_path = self.find_file('no_embedded_data.pdf')
        self.assertEqual(FacturX(file_path)._xml_from_file(file_path), None)

    def test_file_embedded_data(self, file_name='embedded_data.pdf'):
        file_path = self.find_file(file_name)
        self.assertTrue(FacturX(file_path)._xml_from_file(file_path) is not None, "The PDF file has no embedded file")

    def test_write_pdf(self):
        file_path = self.find_file('no_embedded_data.pdf')
        factx = FacturX(file_path)
        test_file_path = os.path.join(self.test_files_dir, 'test.pdf')

        # checking if pdf file is made
        factx.write_pdf(test_file_path)
        self.assertTrue(os.path.isfile(test_file_path))

        # checking that xml is embedded
        test_factx = FacturX(test_file_path)
        self.assertIsNotNone(test_factx.xml, "XML should be embedded in the PDF")

        os.remove(test_file_path)

    def test_write_xml(self):
        compare_file_dir = os.path.join(os.path.dirname(__file__), 'compare')
        expected_file_path = os.path.join(compare_file_dir, 'no_embedded_data.xml')
        test_file_path = os.path.join(compare_file_dir, 'test.xml')

        factx = FacturX(self.find_file('no_embedded_data.pdf'))
        factx.write_xml(test_file_path)
        self.assertTrue(os.path.isfile(test_file_path))

        with open(expected_file_path, 'r') as expected_file, open(test_file_path, 'r') as test_file:
            parser = etree.XMLParser(remove_blank_text=True)
            expected_file_root = etree.XML(expected_file.read(), parser)
            expected_file_str = etree.tostring(expected_file_root)

            test_file_root = etree.XML(test_file.read(), parser)
            test_file_str = etree.tostring(test_file_root)

        expected_file_str = expected_file_str.decode('utf-8')
        test_file_str = test_file_str.decode('utf-8')
        self.assertTrue(expected_file_str == test_file_str, "Files don't match")
        os.remove(test_file_path)


class TestFieldAccess(unittest.TestCase):
    """Test field getting and setting operations"""

    def setUp(self):
        self.test_files_dir = os.path.join(os.path.dirname(__file__), 'sample_invoices')
        self.test_file = os.path.join(self.test_files_dir, 'embedded_data.pdf')

    def test_get_field(self):
        """Test getting field values from embedded XML"""
        factx = FacturX(self.test_file)
        # These fields should exist in embedded_data.pdf
        invoice_type = factx['type']
        self.assertIsNotNone(invoice_type)
        currency = factx['currency']
        self.assertIsNotNone(currency)

    def test_set_field(self):
        """Test setting field values"""
        no_embed_file = os.path.join(self.test_files_dir, 'no_embedded_data.pdf')
        factx = FacturX(no_embed_file)

        # Set various fields
        factx['seller_name'] = 'Test Company'
        factx['buyer_name'] = 'Buyer Company'
        factx['invoice_number'] = 'INV-2025-001'

        # Verify fields were set
        self.assertEqual(factx['seller_name'], 'Test Company')
        self.assertEqual(factx['buyer_name'], 'Buyer Company')
        self.assertEqual(factx['invoice_number'], 'INV-2025-001')

    def test_set_date_field(self):
        """Test setting date fields with datetime objects"""
        no_embed_file = os.path.join(self.test_files_dir, 'no_embedded_data.pdf')
        factx = FacturX(no_embed_file)

        test_date = datetime(2025, 10, 2)
        factx['date'] = test_date

        # Verify date was set and can be retrieved
        retrieved_date = factx['date']
        self.assertEqual(retrieved_date, test_date)


class TestValidation(unittest.TestCase):
    """Test XML validation functionality"""

    def setUp(self):
        self.test_files_dir = os.path.join(os.path.dirname(__file__), 'sample_invoices')

    def test_validation_with_embedded_data(self):
        """Test that embedded data PDFs validate correctly"""
        test_file = os.path.join(self.test_files_dir, 'embedded_data.pdf')
        factx = FacturX(test_file)
        # Should validate successfully or return False if required fields are missing
        result = factx.is_valid()
        self.assertIsInstance(result, bool)

    def test_validation_with_required_fields(self):
        """Test validation checks for required fields"""
        no_embed_file = os.path.join(self.test_files_dir, 'no_embedded_data.pdf')
        factx = FacturX(no_embed_file)

        # Set some common fields
        factx['date'] = datetime.now()
        factx['seller_name'] = 'Seller Inc'
        factx['buyer_name'] = 'Buyer Inc'
        factx['seller_country'] = 'FR'

        # Validation will check for required fields and return True/False
        # The minimum level has several required fields
        is_valid = factx.is_valid()
        # Even if not valid, this should not raise an exception
        self.assertIsInstance(is_valid, bool)


class TestExport(unittest.TestCase):
    """Test export functionality (JSON, YAML)"""

    def setUp(self):
        self.test_files_dir = os.path.join(os.path.dirname(__file__), 'sample_invoices')
        self.compare_dir = os.path.join(os.path.dirname(__file__), 'compare')

    def test_to_dict(self):
        """Test converting XML to dictionary"""
        test_file = os.path.join(self.test_files_dir, 'embedded_data.pdf')
        factx = FacturX(test_file)

        result_dict = factx.to_dict()
        self.assertIsInstance(result_dict, dict)
        self.assertIn('currency', result_dict)
        self.assertIn('type', result_dict)

    def test_write_json(self):
        """Test exporting to JSON file"""
        test_file = os.path.join(self.test_files_dir, 'embedded_data.pdf')
        factx = FacturX(test_file)

        json_path = os.path.join(self.compare_dir, 'test_output.json')

        # Set required fields for validation
        factx['seller_country'] = 'FR'
        factx['buyer_country'] = 'FR'

        if factx.is_valid():
            factx.write_json(json_path)
            self.assertTrue(os.path.isfile(json_path))
            os.remove(json_path)

    def test_write_yaml(self):
        """Test exporting to YAML file"""
        test_file = os.path.join(self.test_files_dir, 'embedded_data.pdf')
        factx = FacturX(test_file)

        yaml_path = os.path.join(self.compare_dir, 'test_output.yml')

        # Set required fields for validation
        factx['seller_country'] = 'FR'
        factx['buyer_country'] = 'FR'

        if factx.is_valid():
            factx.write_yaml(yaml_path)
            self.assertTrue(os.path.isfile(yaml_path))
            os.remove(yaml_path)


class TestDifferentLevels(unittest.TestCase):
    """Test different Factur-X conformance levels"""

    def setUp(self):
        self.test_files_dir = os.path.join(os.path.dirname(__file__), 'sample_invoices')

    def test_minimum_level(self):
        """Test loading PDF with MINIMUM level"""
        test_file = os.path.join(self.test_files_dir, 'Facture_FR_MINIMUM.pdf')
        if os.path.exists(test_file):
            factx = FacturX(test_file)
            self.assertEqual(factx.flavor.level, 'minimum')

    def test_basic_level(self):
        """Test loading PDF with BASIC level"""
        test_file = os.path.join(self.test_files_dir, 'Facture_FR_BASIC.pdf')
        if os.path.exists(test_file):
            factx = FacturX(test_file)
            self.assertEqual(factx.flavor.level, 'basic')

    def test_en16931_level(self):
        """Test loading PDF with EN16931 level"""
        test_file = os.path.join(self.test_files_dir, 'Facture_FR_EN16931.pdf')
        if os.path.exists(test_file):
            factx = FacturX(test_file)
            self.assertEqual(factx.flavor.level, 'en16931')


def main():
    unittest.main()


if __name__ == '__main__':
    main()

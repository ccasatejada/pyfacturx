# pyfacturx

Python library for creating and manipulating Factur-X compliant invoices - PDF documents with embedded XML metadata following the French/European electronic invoicing standard (FNFE).

## Overview

**Factur-X** is a Franco-European e-invoicing standard that combines a human-readable PDF with structured XML data embedded in the same file. This hybrid format allows invoices to be:
- Read and archived by humans (PDF layer)
- Automatically processed by accounting software (XML layer)
- Compliant with PDF/A-3 archiving standards

This library provides a simple Python interface for:
- Reading and extracting Factur-X metadata from existing PDFs
- Creating new Factur-X compliant invoices from regular PDFs
- Editing invoice fields through a Python dictionary interface
- Validating XML against official XSD schemas
- Exporting metadata to various formats (XML, JSON, YAML)

## Key Features

- **Simple Dictionary-Style API** - Access invoice fields like `inv['seller_name']` or `inv['total_amount']`
- **Multiple Conformance Levels** - Support for MINIMUM, BASIC, BASIC WL, and EN 16931 profiles
- **PDF/A-3 Compliance** - Automatically embeds ICC color profiles and PDF/A-3 metadata
- **XSD Validation** - Validate XML against official Factur-X schemas
- **Format Conversion** - Export to XML, JSON, or YAML for data exchange
- **Template System** - Create new invoices from XML templates
- **Python 3.9+** - Modern codebase using current libraries (pypdf, lxml)

## Installation

## Quick Start

### Creating a Factur-X Invoice

```python
from facturx import FacturX
from datetime import datetime

# Load a regular PDF (without embedded XML)
inv = FacturX('invoice.pdf')

# Set invoice fields
inv['invoice_number'] = 'INV-2025-001'
inv['date'] = datetime(2025, 10, 2)
inv['seller_name'] = 'My Company Ltd.'
inv['buyer_name'] = 'Customer Inc.'
inv['seller_country'] = 'FR'
inv['buyer_country'] = 'DE'
inv['currency'] = 'EUR'

# Validate and save
if inv.is_valid():
    inv.write_pdf('facturx-invoice.pdf')
```

### Reading an Existing Factur-X Invoice

```python
from facturx import FacturX

# Load a PDF with embedded Factur-X XML
inv = FacturX('facturx-invoice.pdf')

# Access fields
print(f"Invoice: {inv['invoice_number']}")
print(f"Seller: {inv['seller_name']}")
print(f"Amount: {inv['amount_total']} {inv['currency']}")
print(f"Date: {inv['date']}")

# Get all fields as dictionary
data = inv.to_dict()
```

### Exporting Metadata

```python
from facturx import FacturX

inv = FacturX('facturx-invoice.pdf')

# Export XML only
inv.write_xml('metadata.xml')

# Export to JSON
inv.write_json('metadata.json')

# Export to YAML
inv.write_yaml('metadata.yml')
```

## Command Line Interface

After installing the package with `pip install -e .`, you can use the command line tool. If the `facturx` command is not found in your PATH, you can run it using Python:

```bash
# Using Python module (always works)
python -m bin.cli <command> [options]

# Or if installed and in PATH
facturx <command> [options]
```

### Available Commands

#### Dump embedded metadata to file

```bash
# Extract to XML
python -m bin.cli dump invoice.pdf metadata.xml

# Extract to JSON
python -m bin.cli dump invoice.pdf metadata.json

# Extract to YAML
python -m bin.cli dump invoice.pdf metadata.yml
```

#### Validate embedded XML

```bash
python -m bin.cli validate invoice.pdf
```

### Help

```bash
# Show all available commands
python -m bin.cli -h

# Show help for specific command
python -m bin.cli dump -h
python -m bin.cli validate -h
```

## Available Fields

The library provides a simplified interface to common invoice fields. Field names are mapped to XML paths internally. See `facturx/flavors/fields.yml` for the complete field mapping.

**Common fields include:**
- `invoice_number`, `date`, `date_due`
- `seller_name`, `seller_country`, `seller_tva_intra`, `seller_siret`
- `buyer_name`, `buyer_country`, `buyer_siret`
- `currency`, `amount_untaxed`, `amount_tax`, `amount_total`
- `type` (380=Invoice, 381=Credit Note)

## Conformance Levels

Factur-X defines several conformance levels with increasing requirements:

- **MINIMUM** - Basic invoice identification and totals
- **BASIC WL** - Basic with line items (without VAT breakdown)
- **BASIC** - Basic with full line items
- **EN 16931** - Full European standard compliance (recommended)

Specify the level when creating new invoices:

```python
inv = FacturX('invoice.pdf', level='en16931')
```

## Testing

The library includes comprehensive test coverage:

```bash
# Run all tests
python -m unittest facturx.tests.test_facturx -v

# Run specific test class
python -m unittest facturx.tests.test_facturx.TestFieldAccess -v

# Run single test
python -m unittest facturx.tests.test_facturx.TestReading.test_write_pdf
```

## Requirements

- Python 3.9 or higher
- lxml 6.0.2
- pypdf 6.1.1
- pycountry 20.7.3
- PyYAML 6.0.1

See `requirements.txt` for exact versions.

## Project History

This project is a continuation of previous Factur-X libraries:

1. Originally forked from [Akretion's factur-x](https://github.com/akretion/factur-x)
2. Then forked from [invoice-x's factur-x-ng](https://github.com/invoice-x/factur-x-ng)
3. Then forked from [cnfilms' factur-x-ng](https://github.com/cnfilms/factur-x-ng)

Our goals:
- Maintain compatibility with Python 3.9+
- Use modern, maintained libraries (pypdf instead of deprecated PyPDF2)
- Focus exclusively on Factur-X standard
- Provide comprehensive test coverage
- Simple, intuitive API

## License

BSD License (same as upstream projects)


## Resources

- [Factur-X Official Documentation (FNFE)](https://fnfe-mpe.org/factur-x/)
- [EN 16931 European Standard](https://ec.europa.eu/digital-building-blocks/wikis/display/DIGITAL/Obtaining+a+copy+of+the+European+standard+on+eInvoicing)
- [AIFE - Association Française des Entreprises privées](https://www.aife.fr/)

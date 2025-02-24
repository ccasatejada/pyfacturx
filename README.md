# pyfacturx 
  
Python lib to make Factur-X (AIFE's hybrid standard): PDF with embedded xml
  
  

Factur-X Python library
=======================

Factur-X is a EU standard for embedding XML representations of invoices
in PDF files. This library provides an interface for reading, editing
and saving the this metadata.

Since there are multiple flavors of the embedded XML data, this library
abstracts them into a Python ``dict``, which can be used to load and
save from/to different flavors.

1)  
This project was forked from `Akretion <https://github.com/akretion/factur-x>`_ and continues to be under the same license. We aim to make the library higher-level, make editing fields easier and support more standards and flavors.  
2)  
This project was forked from `invoice-x <https://github.com/invoice-x/factur-x-ng>`_ and continues to be under the same license. We aim only on factur-x standard, make it simplier and exhaustive around the different data profile provided by the standard
3)  
This project was forked from `cnfilms <https://github.com/cnfilms/factur-x-ng>`_ and continues to be under the same license. We aim on maintaining the library to be installable and usable >python3.9 and avoid use of deprecated lib (like pypdf2).

 
  

Main features:
--------------

-  Edit and save existing XML metadata fields.
-  Create new XML representation from template and embed in PDF.
-  Add existing XML representation to PDF.
-  Validate existing XML representation.

Installation
------------

::

   pip install -r requirements.txt

::

Installation on your personal project
------------

::

   pip install https://github.com/ccasatejada/pyfacturx/archive/main.zip

::

Usage
-----

Load PDF file without XML and assign some values to common fields.

::

   from facturx import FacturX

   inv = FacturX('some-file.pdf')
   inv['due_date'] = datetime(2018, 10, 10)
   inv['seller_name'] = 'Smith Ltd.'
   inv['buyer_country'] = 'France'

see fields mapping between xml and which key are available in facturx/flavors/fields.yml

Validate and save PDF including XML representation.

::

   inv.is_valid()
   inv.write_pdf('my-file.pdf')

Load PDF *with* XML embedded. View and update fields via pivot dict.

::

   inv = FacturX('another-file.pdf')
   inv_dict = inv.as_dict()
   inv_dict['currency'] = 'USD'
   inv.update(inv_dict)

Save XML metadata in separate file in different formats.

::

   inv.write_xml('metadata.xml')
   inv.write_json('metadata.json')
   inv.write_yaml('metadata.yml')

To have more examples, look at the source code of the command line tools
located in the *bin* subdirectory.

Command line tools
------------------

Several sub-commands are provided with this lib:

-  Dump embedded metadata:   ``facturx dump file-with-xml.pdf metadata.(xml|json|yml)``
-  Validate existing metadata: ``facturx validate file-with-xml.pdf``
-  Add external metadata file: ``facturx add no-xml.pdf metadata.xml``
-  Extract fields from PDF and embed: ``facturx extract no-xml.pdf``

All these command line tools have a **-h** option that explains how to
use them and shows all the available options.

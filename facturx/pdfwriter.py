import hashlib
import io
from datetime import datetime

from lxml import etree
from pypdf import PdfWriter, PdfReader
from pypdf.generic import DictionaryObject, DecodedStreamObject, NameObject, create_string_object, ArrayObject

from .logger import logger

# Python 2 and 3 compat
try:
    file_types = (file, io.IOBase)
except NameError:
    file_types = (io.IOBase,)
unicode = str

class FacturXPDFWriter(PdfWriter):
    def __init__(self, facturx, pdf_metadata=None):
        """Take a FacturX instance and write the XML to the attached PDF file"""

        super().__init__()
        self.factx = facturx

        original_pdf = PdfReader(facturx.pdf)
        # Extract /OutputIntents obj from original invoice
        output_intents = _get_original_output_intents(original_pdf)
        self.append_pages_from_reader(original_pdf)

        original_pdf_id = original_pdf.trailer.get("/ID")
        logger.debug('original_pdf_id=%s', original_pdf_id)
        if original_pdf_id:
            self._ID = original_pdf_id

        if pdf_metadata is None:
            base_info = {
                'seller': self.factx['seller_name'],
                'number': self.factx['invoice_number'],
                'date': self.factx['date'],
                'doc_type': self.factx['type'],
            }
            pdf_metadata = _base_info2pdf_metadata(base_info)
        else:
            # clean-up pdf_metadata dict
            for key, value in pdf_metadata.items():
                if not isinstance(value, (str, unicode)):
                    pdf_metadata[key] = ''

        self._update_metadata_add_attachment(pdf_metadata, output_intents)

    def _update_metadata_add_attachment(self, pdf_metadata, output_intents):
        # The entry for the file
        facturx_xml_str = self.factx.xml_str
        md5sum = hashlib.md5().hexdigest()
        md5sum_obj = create_string_object(md5sum)
        params_dict = DictionaryObject({
            NameObject('/CheckSum'): md5sum_obj,
            NameObject('/ModDate'): create_string_object(_get_pdf_timestamp()),
            NameObject('/Size'): NameObject(str(len(facturx_xml_str))),
        })
        file_entry = DecodedStreamObject()
        file_entry.set_data(facturx_xml_str)  # here we integrate the file itself
        file_entry.update({
            NameObject("/Type"): NameObject("/EmbeddedFile"),
            NameObject("/Params"): params_dict,
            NameObject("/Subtype"): NameObject("/text#2Fxml"),
        })
        file_entry_obj = self._add_object(file_entry)
        # The Filespec entry
        ef_dict = DictionaryObject({
            NameObject("/F"): file_entry_obj,
            NameObject('/UF'): file_entry_obj,
        })

        xmp_filename = self.factx.flavor.details['xmp_filename']
        fname_obj = create_string_object(xmp_filename)
        filespec_dict = DictionaryObject({
            NameObject("/AFRelationship"): NameObject("/Data"),
            NameObject("/Desc"): create_string_object("Factur-X Invoice"),
            NameObject("/Type"): NameObject("/Filespec"),
            NameObject("/F"): fname_obj,
            NameObject("/EF"): ef_dict,
            NameObject("/UF"): fname_obj,
        })
        filespec_obj = self._add_object(filespec_dict)
        name_arrayobj_cdict = {fname_obj: filespec_obj}

        logger.debug('name_arrayobj_cdict=%s', name_arrayobj_cdict)
        name_arrayobj_content_sort = list(
            sorted(name_arrayobj_cdict.items(), key=lambda x: x[0]))
        logger.debug('name_arrayobj_content_sort=%s', name_arrayobj_content_sort)
        name_arrayobj_content_final = []
        af_list = []
        for (fname_obj, filespec_obj) in name_arrayobj_content_sort:
            name_arrayobj_content_final += [fname_obj, filespec_obj]
            af_list.append(filespec_obj)
        embedded_files_names_dict = DictionaryObject({
            NameObject("/Names"): ArrayObject(name_arrayobj_content_final),
        })

        # Then create the entry for the root, as it needs a
        # reference to the Filespec
        embedded_files_dict = DictionaryObject({
            NameObject("/EmbeddedFiles"): embedded_files_names_dict,
        })
        res_output_intents = []
        logger.debug('output_intents=%s', output_intents)
        for output_intent_dict, dest_output_profile_dict in output_intents:
            dest_output_profile_obj = self._add_object(dest_output_profile_dict)
            output_intent_dict.update({
                NameObject("/DestOutputProfile"): dest_output_profile_obj,
            })
            output_intent_obj = self._add_object(output_intent_dict)
            res_output_intents.append(output_intent_obj)

        # Update the root
        xmp_level_str = self.factx.flavor.details['levels'][self.factx.flavor.level]['xmp_str']
        xmp_template = self.factx.flavor.get_xmp_xml()
        metadata_xml_str = _prepare_pdf_metadata_xml(xmp_level_str, xmp_filename, xmp_template, pdf_metadata)
        metadata_file_entry = DecodedStreamObject()
        metadata_file_entry.set_data(metadata_xml_str)
        metadata_file_entry.update({
            NameObject('/Subtype'): NameObject('/XML'),
            NameObject('/Type'): NameObject('/Metadata'),
        })
        metadata_obj = self._add_object(metadata_file_entry)
        af_value_obj = self._add_object(ArrayObject(af_list))
        self._root_object.update({
            NameObject("/AF"): af_value_obj,
            NameObject("/Metadata"): metadata_obj,
            NameObject("/Names"): embedded_files_dict,
            NameObject("/PageMode"): NameObject("/UseAttachments"),
        })
        logger.debug('res_output_intents=%s', res_output_intents)
        if res_output_intents:
            self._root_object.update({
                NameObject("/OutputIntents"): ArrayObject(res_output_intents),
            })
        metadata_txt_dict = _prepare_pdf_metadata_txt(pdf_metadata)
        self.add_metadata(metadata_txt_dict)

def _get_metadata_timestamp():
    now_dt = datetime.now()
    meta_date = now_dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
    return meta_date

def _base_info2pdf_metadata(base_info):
    doc_type_name = u'Refund' if base_info['doc_type'] == '381' else u'Invoice'
    date_to_format = datetime.today() if not base_info.get('date', None) else base_info.get('date')
    date_str = datetime.strftime(date_to_format, '%Y-%m-%d')
    title = f"{base_info['seller']}: {doc_type_name} {base_info['number']}"
    subject = f"Factur-X {doc_type_name} {base_info['number']} dated {date_str} issued by {base_info['seller']}"
    pdf_metadata = {
        'author': base_info['seller'],
        'keywords': f"{doc_type_name}, Factur-X",
        'title': title,
        'subject': subject,
    }
    logger.debug('Converted base_info to pdf_metadata: %s', pdf_metadata)
    return pdf_metadata

def _prepare_pdf_metadata_txt(pdf_metadata):
    pdf_date = _get_pdf_timestamp()
    info_dict = {
        '/Author': pdf_metadata.get('author', ''),
        '/CreationDate': pdf_date,
        '/Creator': 'factur-x Python lib',
        '/Keywords': pdf_metadata.get('keywords', ''),
        '/ModDate': pdf_date,
        '/Subject': pdf_metadata.get('subject', ''),
        '/Title': pdf_metadata.get('title', ''),
    }
    return info_dict

def _prepare_pdf_metadata_xml(xmp_level_str, xmp_filename, facturx_ext_schema_root, pdf_metadata):
    nsmap_x = {'x': 'adobe:ns:meta/'}
    nsmap_rdf = {'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'}
    nsmap_dc = {'dc': 'http://purl.org/dc/elements/1.1/'}
    nsmap_pdf = {'pdf': 'http://ns.adobe.com/pdf/1.3/'}
    nsmap_xmp = {'xmp': 'http://ns.adobe.com/xap/1.0/'}
    nsmap_pdfaid = {'pdfaid': 'http://www.aiim.org/pdfa/ns/id/'}
    nsmap_fx = {'fx': 'urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#'}
    ns_x = '{%s}' % nsmap_x['x']
    ns_dc = '{%s}' % nsmap_dc['dc']
    ns_rdf = '{%s}' % nsmap_rdf['rdf']
    ns_pdf = '{%s}' % nsmap_pdf['pdf']
    ns_xmp = '{%s}' % nsmap_xmp['xmp']
    ns_pdfaid = '{%s}' % nsmap_pdfaid['pdfaid']
    ns_fx = '{%s}' % nsmap_fx['fx']
    ns_xml = '{http://www.w3.org/XML/1998/namespace}'

    root = etree.Element(ns_x + 'xmpmeta', nsmap=nsmap_x)
    rdf = etree.SubElement(root, ns_rdf + 'RDF', nsmap=nsmap_rdf)
    desc_pdfaid = etree.SubElement(rdf, ns_rdf + 'Description', nsmap=nsmap_pdfaid)
    desc_pdfaid.set(ns_rdf + 'about', '')
    etree.SubElement(desc_pdfaid, ns_pdfaid + 'part').text = '3'
    etree.SubElement(desc_pdfaid, ns_pdfaid + 'conformance').text = 'B'
    desc_dc = etree.SubElement(rdf, ns_rdf + 'Description', nsmap=nsmap_dc)
    desc_dc.set(ns_rdf + 'about', '')
    dc_title = etree.SubElement(desc_dc, ns_dc + 'title')
    dc_title_alt = etree.SubElement(dc_title, ns_rdf + 'Alt')
    dc_title_alt_li = etree.SubElement(dc_title_alt, ns_rdf + 'li')
    dc_title_alt_li.text = pdf_metadata.get('title', '')
    dc_title_alt_li.set(ns_xml + 'lang', 'x-default')
    dc_creator = etree.SubElement(desc_dc, ns_dc + 'creator')
    dc_creator_seq = etree.SubElement(dc_creator, ns_rdf + 'Seq')
    etree.SubElement(dc_creator_seq, ns_rdf + 'li').text = pdf_metadata.get('author', '')
    dc_desc = etree.SubElement(desc_dc, ns_dc + 'description')
    dc_desc_alt = etree.SubElement(dc_desc, ns_rdf + 'Alt')
    dc_desc_alt_li = etree.SubElement(dc_desc_alt, ns_rdf + 'li')
    dc_desc_alt_li.text = pdf_metadata.get('subject', '')
    dc_desc_alt_li.set(ns_xml + 'lang', 'x-default')
    desc_adobe = etree.SubElement(rdf, ns_rdf + 'Description', nsmap=nsmap_pdf)
    desc_adobe.set(ns_rdf + 'about', '')
    producer = etree.SubElement(desc_adobe, ns_pdf + 'Producer')
    producer.text = 'PyPDF2'
    desc_xmp = etree.SubElement(rdf, ns_rdf + 'Description', nsmap=nsmap_xmp)
    desc_xmp.set(ns_rdf + 'about', '')
    creator = etree.SubElement(desc_xmp, ns_xmp + 'CreatorTool')
    creator.text = 'factur-x python lib'
    timestamp = _get_metadata_timestamp()
    etree.SubElement(desc_xmp, ns_xmp + 'CreateDate').text = timestamp
    etree.SubElement(desc_xmp, ns_xmp + 'ModifyDate').text = timestamp

    facturx_ext_schema_desc_xpath = facturx_ext_schema_root.xpath('//rdf:Description', namespaces=nsmap_rdf)
    rdf.append(facturx_ext_schema_desc_xpath[1])
    facturx_desc = etree.SubElement(rdf, ns_rdf + 'Description', nsmap=nsmap_fx)
    facturx_desc.set(ns_rdf + 'about', '')
    facturx_desc.set(ns_fx + 'ConformanceLevel', xmp_level_str)
    facturx_desc.set(ns_fx + 'DocumentFileName', xmp_filename)
    facturx_desc.set(ns_fx + 'DocumentType', 'INVOICE')
    facturx_desc.set(ns_fx + 'Version', '1.0')

    xml_str = etree.tostring(root, pretty_print=True, encoding="UTF-8", xml_declaration=False)
    head = u'<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>'.encode('utf-8')
    tail = u'<?xpacket end="w"?>'.encode('utf-8')
    xml_final_str = head + xml_str + tail
    logger.debug('metadata XML:')
    return xml_final_str

def _get_original_output_intents(original_pdf):
    output_intents = []
    try:
        pdf_root = original_pdf.trailer['/Root']
        ori_output_intents = pdf_root['/OutputIntents']
        logger.debug('output_intents_list=%s', ori_output_intents)
        for ori_output_intent in ori_output_intents:
            ori_output_intent_dict = ori_output_intent.get_object()
            logger.debug('ori_output_intents_dict=%s', ori_output_intent_dict)
            dest_output_profile_dict = ori_output_intent_dict['/DestOutputProfile'].get_object()
            output_intents.append((ori_output_intent_dict, dest_output_profile_dict))
    except:
        pass
    return output_intents

def _get_pdf_timestamp(date=None):
    if date is None:
        date = datetime.now()
    pdf_date = date.strftime("D:%Y%m%d%H%M%S+00'00'")
    return pdf_date

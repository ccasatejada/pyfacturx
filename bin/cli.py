import argparse

from facturx.facturx import *
from facturx.logger import logger


def main():
    parser = argparse.ArgumentParser(
        description='PDF invoice with embedded XML' +
        ' metadata following the Factur-X standard')
    subparsers = parser.add_subparsers(
        help='sub-command help', dest="sub_command")

    parser_dump = subparsers.add_parser(
        'dump', help='dump xml meta data to xml|json, takes two arguments')
    parser_dump.add_argument('pdf_invoice', type=argparse.FileType('r'),
                             help='pdf invoice containing embedded xml')
    parser_dump.add_argument(
        'output_file', type=str, help='name of export file')

    parser_validate = subparsers.add_parser(
        'validate', help='validate xml meta data from pdf invoice')
    parser_validate.add_argument('pdf_invoice', type=argparse.FileType('r'),
                                 help='pdf invoice to validate')

    args = parser.parse_args()

    if args.sub_command == 'dump':
        factx = FacturX(args.pdf_invoice.name)
        try:
            output_format = args.output_file.split('.')[1]
            if output_format == 'json':
                factx.write_json(args.output_file)
            elif output_format == 'xml':
                factx.write_xml(args.output_file)
            elif output_format == 'yml':
                factx.write_yaml(args.output_file)
        except IndexError:
            logger.error("No extension to output file provided")

    if args.sub_command == 'validate':
        factx = FacturX(args.pdf_invoice.name)
        factx.is_valid()


if __name__ == '__main__':
    main()

# Copyright 2012-2020 Akretion France (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, date as datelib
import unicodecsv
from tempfile import TemporaryFile
import base64
import logging

logger = logging.getLogger(__name__)
try:
    import xlrd
except ImportError:
    logger.debug('Cannot import xlrd')


class AccountMoveImport(models.TransientModel):
    _inherit = "account.move.import"

    file_format = fields.Selection(selection_add=[('nexans_xls', 'Nexans XLSX')], ondelete={'nexans_xls': 'cascade'})

    def file2pivot(self, fileobj, file_bytes):
        file_format = self.file_format

        if file_format == 'nexans_xls':
            return self.nexans_xls2pivot(file_bytes)
        else:
            return super(AccountMoveImport, self).file2pivot(fileobj, file_bytes)

    def nexans_xls2pivot(self, file_bytes):
        """ Read file content, using xlrd lib """
        book = xlrd.open_workbook(file_contents=file_bytes)
        sheet = book.sheet_by_index(0)

        i = 0
        res = []
        for rownum in range(sheet.nrows):
            row = sheet.row_values(rownum)
            i += 1
            if not row[0]:
                continue
            date = datetime(*xlrd.xldate_as_tuple(row[0], book.datemode))
            vals = {
                'account': str(row[2]),
                'name': str(row[5]),
                'debit': float(row[6] or 0.0),
                'credit': float(row[7] or 0.0),
                'line': i,
                'date': date.strftime('%Y-%m-%d'),
            }
            res.append(vals)
        return res

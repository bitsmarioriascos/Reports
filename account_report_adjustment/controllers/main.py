# -*- coding: utf-8 -*-

import operator
import json
import functools

import werkzeug
import werkzeug.exceptions
import werkzeug.utils
import werkzeug.wrappers
import werkzeug.wsgi

from odoo import http, tools
from odoo.http import (
    request,
    content_disposition,
    serialize_exception as _serialize_exception
)
from odoo.tools import pycompat, float_repr

from odoo.addons.web.controllers.main import (
        ExportFormat,
        GroupsTreeNode,
        ExcelExport,
        GroupExportXlsxWriter,
        ExportXlsxWriter,
    )


def serialize_exception(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return werkzeug.exceptions.InternalServerError(json.dumps(error))
    return wrap


class ExcelExportI(ExcelExport, ExportFormat):

    @http.route('/web/export/xlsx', type='http', auth="user")
    @serialize_exception
    def index(self, data, token):
        return self.base(data, token)

    def from_group_data(self, fields, groups):
        with ExtendGroupExportXlsxWriter(fields, groups.count) as xlsx_writer:
            x, y = 1, 0

            for group_name, group in groups.children.items():
                x, y = xlsx_writer.write_group(x, y, group_name, group)
        return xlsx_writer.value


class ExtendGroupExportXlsxWriter(GroupExportXlsxWriter, ExportXlsxWriter):

    def _write_group_header(self, row, column, label, group, group_depth=0):
        aggregates = group.aggregated_values
        label = '%s%s (%s)' % ('    ' * group_depth, label, group.count)
        self.write(row, column, label, self.header_bold_style)

        if any(f.get('type') == 'monetary' for f in self.fields[1:]):
            decimal_places = [
                res['decimal_places'] for res in group._model
                .env['res.currency'].search_read(
                    [], ['decimal_places']
                )
            ]
            decimal_places = max(decimal_places) if decimal_places else 2

        for field in self.fields[1:]:
            column += 1
            aggregated_value = aggregates.get(field['name'])

            if isinstance(aggregated_value, float):
                if field.get('type') == 'monetary':
                    aggregated_value = float_repr(
                        aggregated_value,
                        decimal_places
                    )
                    aggregated_value = aggregated_value.replace('.', ",")

                elif not field.get('store'):
                    aggregated_value = float_repr(aggregated_value, 2)

            self.write(
                row, column,
                str(
                    aggregated_value if aggregated_value is not None else ''
                ), self.header_bold_style
            )
        return row + 1, 0

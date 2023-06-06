# -*- coding: utf-8 -*-
import io

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang, xlsxwriter

GENERAL_LEDGER = "account.general.ledger"


class AccountReportAdjustment(models.AbstractModel):
    _inherit = 'account.report'

    def _change_lines(self, lines, report_type):
        level_exception = [2, 3]
        if self.report_type != 5:
            lines = self._change_lines_with_record_0(lines, self.report_type)

        if self.report_type not in level_exception:
            lines = self._change_lines_with_title_0(
                lines,
                self.report_type
            )
        return lines

    def _change_lines_with_title_0(self, lines, report_type):
        ref_lines = []
        title_levels = [0, 1, 2]
        level_exception = [2, 3, 5]

        if report_type == 4:
            title_levels = [0]

        for i in range(len(lines)):
            flag = False
            if report_type not in level_exception and \
                    lines[i]['level'] in title_levels and \
                    lines[i]['columns'][-1]['name'] == 0.0:
                line_id = lines[i]
                next_line_id = lines[i+1]
                flag = True
                if next_line_id['level'] not in title_levels and \
                        line_id['id'] == next_line_id['parent_id']:
                    flag = False
            elif report_type == 5:
                if 'level' in lines[i] and \
                        lines[i]['level'] in [0, 1, 2] and \
                        lines[i]['columns'][-1]['name'] == 0.0:
                    line_id = lines[i]
                    next_line_id = lines[i+1]
                    flag = True
                    if 'parent_id' in next_line_id and\
                            line_id['id'] == next_line_id['parent_id']:
                        flag = False

            if not flag:
                ref_lines.append(lines[i])
        return ref_lines

    def _change_lines_with_record_0(self, lines, report_type):
        ref_lines = []
        title_levels = [0, 1, 2, 3]
        if report_type == 4:
            title_levels = [0]
        for i in range(len(lines)):
            flag = False
            value = lines[i]['columns'][-1]['name']
            if report_type == 1 or report_type == 4:
                if lines[i]['level'] not in title_levels and value == 0.0:
                    flag = True
            elif report_type == 2:
                if value == 0.0 or value == "":
                    flag = True
            elif report_type == 3:
                debit = lines[i]['columns'][-2]['name']
                credit = lines[i]['columns'][-1]['name']
                if debit == "":
                    debit = 0.0
                if credit == "":
                    credit = 0.0

                total = debit - credit
                if total == 0.0:
                    flag = True
            elif report_type == 5:
                if 'level' in lines[i]:
                    if lines[i]['level'] not in [0, 1, 2]:
                        total = lines[i]['columns'][-1]['name']
                        if total == 0.0:
                            flag = True
                else:
                    total = lines[i]['columns'][-1]['name']
                    if total == 0.0:
                        flag = True

            if not flag:
                ref_lines.append(lines[i])
        return ref_lines

    def get_xlsx(self, options, response=None):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        sheet = workbook.add_worksheet(self._get_report_name()[:31])

        date_default_col1_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'font_size': 12,
                'font_color': '#666666',
                'indent': 2,
                'num_format': 'yyyy-mm-dd'
            }
        )
        date_default_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'font_size': 12,
                'font_color': '#666666',
                'num_format': 'yyyy-mm-dd'
            }
        )
        default_col1_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'font_size': 12,
                'font_color': '#666666',
                'indent': 2
            }
        )
        default_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'font_size': 12,
                'font_color': '#666666'
            }
        )
        title_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'bold': True,
                'bottom': 2
            }
        )
        super_col_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'bold': True,
                'align': 'center'
            }
        )
        level_0_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'bold': True,
                'font_size': 13,
                'bottom': 6,
                'font_color': '#666666'
            }
        )
        level_1_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'bold': True,
                'font_size': 13,
                'bottom': 1,
                'font_color': '#666666'
            }
        )
        level_2_col1_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'bold': True,
                'font_size': 12,
                'font_color': '#666666',
                'indent': 1
            }
        )
        level_2_col1_total_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'bold': True,
                'font_size': 12,
                'font_color': '#666666'
            }
        )
        level_2_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'bold': True,
                'font_size': 12,
                'font_color': '#666666'
            }
        )
        level_3_col1_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'font_size': 12,
                'font_color': '#666666',
                'indent': 2
            }
        )
        level_3_col1_total_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'bold': True,
                'font_size': 12,
                'font_color': '#666666',
                'indent': 1
            }
        )
        level_3_style = workbook.add_format(
            {
                'font_name': 'Arial',
                'font_size': 12,
                'font_color': '#666666'
            }
        )

        # Set the first column width to 50
        sheet.set_column(0, 0, 50)

        super_columns = self._get_super_columns(options)
        y_offset = bool(super_columns.get('columns')) and 1 or 0

        sheet.write(y_offset, 0, '', title_style)

        # Todo in master: Try to put this logic elsewhere
        x = super_columns.get('x_offset', 0)
        for super_col in super_columns.get('columns', []):
            cell_content = super_col.get(
                'string', ''
            ).replace('<br/>', ' ').replace('&nbsp;', ' ')
            x_merge = super_columns.get('merge')
            if x_merge and x_merge > 1:
                sheet.merge_range(
                    0, x, 0, x + (x_merge - 1),
                    cell_content, super_col_style
                )
                x += x_merge
            else:
                sheet.write(0, x, cell_content, super_col_style)
                x += 1

        header = self.get_header(options)
        header = self._add_new_header(options, header)

        for row in header:
            x = 0
            for column in row:
                colspan = column.get('colspan', 1)
                header_label = column.get(
                    'name', ''
                ).replace('<br/>', ' ').replace('&nbsp;', ' ')
                if colspan == 1:
                    sheet.write(y_offset, x, header_label, title_style)
                else:
                    sheet.merge_range(
                        y_offset, x, y_offset, x + colspan - 1,
                        header_label, title_style
                    )
                x += colspan
            y_offset += 1
        ctx = self._set_context(options)
        ctx.update(
            {
                'no_format': True,
                'print_mode': True,
                'prefetch_fields': False
            }
        )
        # deactivating the prefetching saves ~35% on get_lines running time
        lines = self.with_context(ctx)._get_lines(options)
        lines = self._add_xlsx_column(lines, ctx, options)

        flag = False

        if "comparison" in options and \
                options["comparison"]["filter"] == "no_comparison" or \
                "comparison" not in options:
            flag = True
        if self.zero_validation and flag:
            lines = self._change_lines(lines, self.report_type)

        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)

        # write all data rows
        for y in range(0, len(lines)):
            level = lines[y].get('level')
            if lines[y].get('caret_options'):
                style = level_3_style
                col1_style = level_3_col1_style
            elif level == 0:
                y_offset += 1
                style = level_0_style
                col1_style = style
            elif level == 1:
                style = level_1_style
                col1_style = style
            elif level == 2:
                style = level_2_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') \
                    and level_2_col1_total_style or level_2_col1_style
            elif level == 3:
                style = level_3_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') \
                    and level_3_col1_total_style or level_3_col1_style
            else:
                style = default_style
                col1_style = default_col1_style

            # write the first column, with a specific
            # style to manage the indentation
            cell_type, cell_value = self._get_cell_type_value(lines[y])
            if cell_type == 'date':
                sheet.write_datetime(
                    y + y_offset,
                    0,
                    cell_value,
                    date_default_col1_style
                )
            else:
                sheet.write(
                    y + y_offset,
                    0,
                    cell_value,
                    col1_style
                )

            # write all the remaining cells
            for x in range(1, len(lines[y]['columns']) + 1):
                cell_type, cell_value = self._get_cell_type_value(
                    lines[y]['columns'][x - 1]
                )
                if cell_type == 'date':
                    sheet.write_datetime(
                        y + y_offset,
                        x + lines[y].get('colspan', 1) - 1,
                        cell_value,
                        date_default_style
                    )
                else:
                    sheet.write(
                        y + y_offset,
                        x + lines[y].get('colspan', 1) - 1,
                        cell_value,
                        style
                    )

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        return generated_file

    def _add_xlsx_column(self, lines, ctx, options):
        active_model = ctx.get('active_model')
        if active_model == "account.aged.payable":
            for line in lines:
                arr = [{"name": line["name"]}]
                for value in line["columns"]:
                    arr.append(value)

                if type(line["id"]) is str:
                    partner_id = line["id"].split("_")
                    try:
                        partner_id = int(partner_id[1])
                        document_num = self._get_partner_data(partner_id, "id")
                        line["name"] = document_num if document_num else ""
                    except ValueError:
                        line["name"] = ""
                line["columns"] = arr
        elif active_model == GENERAL_LEDGER:
            if "hierarchy" not in options or not options["hierarchy"]:
                for line in lines:
                    if "level" in line and line["level"] == 4:
                        const = 0
                        arr = []
                        for value in line["columns"]:
                            if const == 3:
                                partner_name = value["name"]
                                if partner_name:
                                    document_num = self._get_partner_data(
                                        partner_name, "name")
                                    document_num = (
                                        document_num if document_num else None)
                                    arr.append({"name": document_num})
                                else:
                                    arr.append({"name": None})
                            arr.append(value)
                            const += 1
                        line["columns"] = arr
        return lines

    def _get_partner_data(self, data, type):
        partner = self.env["res.partner"].search([
            (type, "=", data),
            ("active", "in", (True, False))
        ], limit=1)
        return partner.vat

    def _add_new_header(self, options, header):
        active_model = self._set_context(options).get("active_model")
        document_number = _('Document Number')
        if active_model == "account.aged.payable":
            for line in header:
                arr = [{'name': document_number}]
                for value in line:
                    arr.append(value)
                header[0] = arr
        elif active_model == GENERAL_LEDGER:
            if "hierarchy" not in options or not options["hierarchy"]:
                for line in header:
                    arr = []
                    const = 0
                    for value in line:
                        if const == 4:
                            arr.append({"name": document_number})
                        arr.append(value)
                        const += 1
                    header[0] = arr

        return header


"""
    report type:
    1 - Normal
    2 - Sin level
    3 - Sin diferencia (totalizacion en cada una de las lineas)
    4 - 0 titulo - 1 linea
    5 - Libro mayor
"""


class AccountFinancialReportInherit(models.AbstractModel):
    _inherit = "account.financial.html.report"
    zero_validation = True
    report_type = 2


class AccountCashFlowInherit(models.AbstractModel):
    _inherit = "account.cash.flow.report"
    zero_validation = True
    report_type = 4


class AccountPartnerLedgerInherit(models.AbstractModel):
    _inherit = "account.partner.ledger"
    zero_validation = False
    report_type = 1


class AccountGeneralLedgerInherit(models.AbstractModel):
    _inherit = GENERAL_LEDGER
    zero_validation = True
    report_type = 5

    def _set_context(self, options):
        ctx = super(AccountGeneralLedgerInherit, self)._set_context(options)
        ctx['active_model'] = 'account.general.ledger'
        return ctx


class AccountConsolidatedJournalInherit(models.AbstractModel):
    _inherit = "account.consolidated.journal"
    zero_validation = False
    report_type = 1


class AccountGenericTaxReportInherit(models.AbstractModel):
    _inherit = "account.generic.tax.report"
    zero_validation = False
    report_type = 1


class AccountAnaliticReportInherit(models.AbstractModel):
    _inherit = "account.analytic.report"
    zero_validation = False
    report_type = 1


class AccountDifferenceNiifColgap(models.AbstractModel):
    _inherit = 'account.difference.niif.colgap'
    zero_validation = True
    report_type = 2


class AccountAgedPayable(models.AbstractModel):
    _inherit = 'account.aged.payable'
    zero_validation = False
    report_type = 1

    def _set_context(self, options):
        ctx = super(AccountAgedPayable, self)._set_context(options)
        ctx['active_model'] = 'account.aged.payable'
        return ctx


class AccountAgedReceivable(models.AbstractModel):
    _inherit = 'account.aged.receivable'
    zero_validation = False
    report_type = 1


class AccountAssetsReport(models.AbstractModel):
    _inherit = 'account.assets.report'
    zero_validation = False
    report_type = 1

# -*- coding: utf-8 -*-
import io

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang, xlsxwriter


class AccountReportAdjustment(models.AbstractModel):
    _inherit = 'account.report'

    def _set_context(self, options):
        """This method will set information inside the context based on the
        options dict as some options need to be in context for the query_get
        method defined in account_move_line"""
        ctx = self.env.context.copy()
        if options.get('date') and options['date'].get('date_from'):
            ctx['date_from'] = options['date']['date_from']
        if options.get('date'):
            ctx['date_to'] = options['date'].get(
                'date_to') or options['date'].get('date')
        if options.get('all_entries') is not None:
            ctx['state'] = options.get('all_entries') and 'all' or 'posted'
        if options.get('journals'):
            ctx['journal_ids'] = [j.get('id') for j in options.get(
                'journals') if j.get('selected')]
        company_ids = []
        if options.get('multi_company'):
            company_ids = [
                c.get('id') for c in options['multi_company']
                if c.get('selected')]
            company_ids = company_ids if len(company_ids) > 0 else [
                c.get('id') for c in options['multi_company']]
        ctx['company_ids'] = len(company_ids) > 0 and company_ids or [
            self.env.company.id]
        if options.get('analytic_accounts'):
            ctx['analytic_account_ids'] = \
                self.env['account.analytic.account'].browse(
                [int(acc) for acc in options['analytic_accounts']])
        if options.get('analytic_tags'):
            ctx['analytic_tag_ids'] = self.env['account.analytic.tag'].browse(
                [int(t) for t in options['analytic_tags']])
        if options.get('partner_ids'):
            ctx['partner_ids'] = self.env['res.partner'].browse(
                [int(partner) for partner in options['partner_ids']])
        if options.get('partner_categories'):
            ctx['partner_categories'] = \
                self.env['res.partner.category'].browse(
                [int(category) for category in options['partner_categories']])
        return ctx

    def get_header(self, options):
        if not options.get('groups', {}).get('ids'):
            columns = self._get_columns_name(options)
            if 'selected_column' in options and self.order_selected_column:
                selected_column = columns[abs(options['selected_column']) - 1]
                if 'sortable' in selected_column.get('class', ''):
                    selected_column['class'] = (
                        options['selected_column'] > 0 and 'up ' or
                        'down ') + selected_column['class']
            return [columns]
        return self._get_columns_name_hierarchy(options)

    def _get_columns_name(self, options):
        return []

    def _get_super_columns(self, options):
        """
        Essentially used when getting the xlsx of a report
        Some reports may need super title cells on top of regular
        columns title, This methods retrieve the formers.
        e.g. in Trial Balance, you can compare periods (super cells)
            and each have debit/credit columns


        @params {dict} options: options for computing the report
        @return {dict}:
            {list(dict)} columns: the dict of the super columns of the
            xlsx report,
                the columns' string is contained into the 'string' key
            {int} merge: optional parameter. Indicates to xlsxwriter
                that it should put the contents of each column into
                the resulting
                cell of the merge of this [merge] number of cells
                -- only merging on one line is supported
            {int} x_offset: tells xlsxwriter it should start writing
            the columns from
                [x_offset] cells on the left
        """
        return {}

    def _get_report_name(self):
        return _('Depreciation Table Report')

    def export_to_xlsx(self, options, response=None):
        def write_with_colspan(sheet, x, y, value, colspan, style):
            if colspan == 1:
                sheet.write(y, x, value, style)
            else:
                sheet.merge_range(y, x, y, x + colspan - 1, value, style)
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        sheet = workbook.add_worksheet(self.name[:31])

        date_default_col1_style = workbook.add_format(
            {'font_name': 'Arial',
             'font_size': 12,
             'font_color': '#666666',
             'indent': 2,
             'num_format': 'yyyy-mm-dd'})
        date_default_style = workbook.add_format(
            {'font_name': 'Arial',
             'font_size': 12,
             'font_color': '#666666',
             'num_format': 'yyyy-mm-dd'})
        default_col1_style = workbook.add_format(
            {'font_name': 'Arial',
             'font_size': 12,
             'font_color': '#666666',
             'indent': 2})
        default_style = workbook.add_format(
            {'font_name': 'Arial',
             'font_size': 12,
             'font_color': '#666666'})
        title_style = workbook.add_format(
            {'font_name': 'Arial',
             'bold': True,
             'bottom': 2})
        level_0_style = workbook.add_format(
            {'font_name': 'Arial',
             'bold': True,
             'font_size': 13,
             'bottom': 6,
             'font_color': '#666666'})
        level_1_style = workbook.add_format(
            {'font_name': 'Arial',
             'bold': True,
             'font_size': 13,
             'bottom': 1,
             'font_color': '#666666'})
        level_2_col1_style = workbook.add_format(
            {'font_name': 'Arial',
             'bold': True,
             'font_size': 12,
             'font_color': '#666666',
             'indent': 1})
        level_2_col1_total_style = workbook.add_format(
            {'font_name': 'Arial',
             'bold': True,
             'font_size': 12,
             'font_color': '#666666'})
        level_2_style = workbook.add_format(
            {'font_name': 'Arial',
             'bold': True,
             'font_size': 12,
             'font_color': '#666666'})
        level_3_col1_style = workbook.add_format(
            {'font_name': 'Arial',
             'font_size': 12,
             'font_color': '#666666',
             'indent': 2})
        level_3_col1_total_style = workbook.add_format(
            {'font_name': 'Arial',
             'bold': True,
             'font_size': 12,
             'font_color': '#666666',
             'indent': 1})
        level_3_style = workbook.add_format(
            {'font_name': 'Arial',
             'font_size': 12,
             'font_color': '#666666'})

        # Set the first column width to 50
        sheet.set_column(0, 0, 50)

        y_offset = 0
        x_offset = 1  # 1 and not 0 to leave space for the line name
        print_mode_self = self.with_context(
            no_format=True, print_mode=True, prefetch_fields=False)
        print_options = print_mode_self._get_options(previous_options=options)
        lines = self._filter_out_folded_children(
            print_mode_self._get_lines(print_options))

        # Add headers.
        # For this, iterate in the same way as done in main_table_header
        # template
        column_headers_render_data = self._get_column_headers_render_data(
            print_options)
        for header_level_index, header_level in \
                enumerate(print_options['column_headers']):
            for header_to_render in header_level * \
                column_headers_render_data['level_repetitions']\
                    [header_level_index]:
                colspan = header_to_render.get(
                    'colspan',
                    column_headers_render_data['level_colspan']
                    [header_level_index])
                write_with_colspan(sheet, x_offset, y_offset,
                                   header_to_render.get(
                                       'name', ''), colspan, title_style)
                x_offset += colspan
            if print_options['show_growth_comparison']:
                write_with_colspan(sheet, x_offset, y_offset,
                                   '%', 1, title_style)
            y_offset += 1
            x_offset = 1

        for subheader in column_headers_render_data['custom_subheaders']:
            colspan = subheader.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset,
                               subheader.get('name', ''), colspan, title_style)
            x_offset += colspan
        y_offset += 1
        x_offset = 1

        for column in print_options['columns']:
            colspan = column.get('colspan', 1)
            write_with_colspan(sheet, x_offset, y_offset,
                               column.get('name', ''), colspan, title_style)
            x_offset += colspan
        y_offset += 1

        if print_options.get('order_column'):
            lines = self._sort_lines(lines, print_options)

        # Add lines.
        for y in range(0, len(lines)):
            level = lines[y].get('level')
            flag = True
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
                col1_style = 'total' in lines[y].get('class', '').split(
                    ' ') and level_2_col1_total_style or level_2_col1_style
            elif level == 3:
                style = level_3_style
                col1_style = 'total' in lines[y].get('class', '').split(
                    ' ') and level_3_col1_total_style or level_3_col1_style
            else:
                style = default_style
                col1_style = default_col1_style

            # write the first column, with a specific style to manage
            # the indentation
            cell_type, cell_value = self._get_cell_type_value(lines[y])
            if cell_type == 'date':
                sheet.write_datetime(
                    y + y_offset, 0, cell_value, date_default_col1_style)
            else:
                sheet.write(y + y_offset, 0, cell_value, col1_style)

            # write all the remaining cells
            for x in range(1, len(lines[y]['columns']) + 1):
                cell_type, cell_value = self._get_cell_type_value(
                    lines[y]['columns'][x - 1]
                )
                value = 0
                zero_validation = False
                handler_models = ['account.cash.flow.report.handler',
                                  'account.partner.ledger.report.handler']
                if self.custom_handler_model_name in handler_models:
                    zero_validation = True
                try:
                    if zero_validation and flag:
                        value = float(lines[y]['columns'][-1]['name'])
                        if level is not None and value == 0.0 and level >= 3:
                            flag = False
                    else:
                        value = cell_value
                except ValueError:
                    value = cell_value
                if flag:
                    if cell_type == 'date':
                        sheet.write_datetime(
                            y + y_offset, x + lines[y].get('colspan', 1) - 1,
                            cell_value, date_default_style
                        )
                    else:
                        sheet.write(
                            y + y_offset, x + lines[y].get('colspan', 1) - 1,
                            cell_value, style
                        )

            # write the first column, with a specific
            # style to manage the indentation
            if flag:
                cell_type, cell_value = self._get_cell_type_value(lines[y])
                if cell_type == 'date':
                    sheet.write_datetime(
                        y + y_offset, 0,
                        cell_value, date_default_col1_style
                    )
                else:
                    sheet.write(y + y_offset, 0, cell_value, col1_style)
            else:
                y_offset = y_offset - 1

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return {
            'file_name': self.get_default_report_filename('xlsx'),
            'file_content': generated_file,
            'file_type': 'xlsx',
        }


class AccountCashFlowInherit(models.AbstractModel):
    _inherit = "account.cash.flow.report.handler"
    zero_validation = True

    zero_validation = fields.Boolean('Zero Validation', default=True)


class AccountPartnerLedgerInherit(models.AbstractModel):
    _inherit = "account.partner.ledger.report.handler"
    zero_validation = True

    zero_validation = fields.Boolean('Zero Validation', default=True)


class AccountGeneralLedgerInherit(models.AbstractModel):
    _inherit = "account.general.ledger.report.handler"
    zero_validation = False

    zero_validation = fields.Boolean('Zero Validation', default=False)


class AccountGenericTaxReportInherit(models.AbstractModel):
    _inherit = "account.generic.tax.report.handler"
    zero_validation = False

    zero_validation = fields.Boolean('Zero Validation', default=False)


class AccountAnaliticReportInherit(models.AbstractModel):
    _inherit = 'account.asset.report.handler'
    zero_validation = False

    zero_validation = fields.Boolean('Zero Validation', default=False)


class AccountAnaliticReportInherit(models.AbstractModel):
    _inherit = 'account.asset.report.handler'
    zero_validation = False

    zero_validation = fields.Boolean('Zero Validation', default=False)
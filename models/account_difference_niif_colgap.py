# -*- coding: utf-8 -*-
import json

from odoo import models, _, fields
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import format_date, get_lang

from datetime import timedelta
from collections import defaultdict


class AccountDifferenceNiifColgap(models.AbstractModel):
    _name = 'account.difference.niif.colgap.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Account Difference NIIF - Colgaap'

    def _dynamic_lines_generator(
            self, report,
            options, all_column_groups_expression_totals):
        lines = self._get_lines_difference_niif_colgap(options)
        lines = [(0, line) for line in lines]
        return lines

    def _get_lines_difference_niif_colgap(self, options):
        account_result = self._get_account_lines_niif_colgap(options)
        all_accounts = {}
        lines = []
        for line in account_result:
            line['amount_niif'] = 0.0
            line['amount_colgap'] = 0.0
            if all_accounts.get(line.get('aa_id'), False):
                account_dict = all_accounts.get(line.get('aa_id'), False)
                account_dict = self._get_value_account(
                    account_dict, line)
                continue
            all_accounts[line.get('aa_id')] = line
            account_dict = all_accounts.get(line.get('aa_id'), False)
            account_dict = self._get_value_account(
                account_dict, line)

        lines = self._get_account_line_report(all_accounts, options)
        return lines

    def _get_sql_select(self, options):
        sql_select = (
            "SELECT aml.id AS aml_id, aml.name AS aml_name, "
            "aml.balance AS BALANCE, aa.id AS aa_id, aa.code AS aa_code, "
            "aa.name AS aa_name, aj.id AS aj_id, aj.name AS aj_name, "
            "aj.type AS aj_type, aj.accounting AS accounting"
        )
        return sql_select

    def _get_sql_from(self, options):
        sql_from = (
            " FROM account_move_line as aml "
            "INNER JOIN account_account as aa ON aa.id=aml.account_id "
            "INNER JOIN account_journal as aj ON aj.id=aml.journal_id "
        )
        return sql_from

    def _get_journal_move(self, options):
        journal_ids = []
        journals = options.get('journals', [])
        for journal in journals:
            if journal.get('selected', False):
                journal_ids.append(journal.get('id'))
        return journal_ids

    def _get_company_move(self, options):
        company_ids = []
        multi_companies = options.get('multi_company', [])
        for company in multi_companies:
            if company.get('selected', False):
                company_ids.append(company.get('id'))
        return company_ids

    def _get_sql_where(self, options):
        params = []
        sql_where = " WHERE 1 = 1 "
        # Date Range
        sql_where += " AND aml.date >= %s AND aml.date <= %s "
        date_range = options.get('date')
        params += [date_range.get('date_from'), date_range.get('date_to')]
        # Journal Ids
        journal_ids = self._get_journal_move(options)
        if journal_ids:
            sql_where += " AND aml.journal_id IN %s "
            params += [tuple(journal_ids)]
        company_ids = self._get_company_move(options)
        if company_ids:
            sql_where += " AND aml.company_id IN %s "
            params += [tuple(company_ids)]
        return sql_where, params

    def _get_sql_orderby(self, options):
        sql_orderby = " ORDER BY aa.code "
        return sql_orderby

    def _get_account_lines_niif_colgap(self, options):
        sql_select = self._get_sql_select(options)
        sql_from = self._get_sql_from(options)
        sql_where, params = self._get_sql_where(options)
        sql_orderby = self._get_sql_orderby(options)
        self.env.cr.execute(sql_select+sql_from+sql_where+sql_orderby, params)
        results = self.env.cr.dictfetchall()
        return results

    def _get_value_account(self, account_dict, line):
        if (line.get('accounting', False) == 'both'
                or line.get('accounting', False) == 'niif'):
            account_dict['amount_niif'] += line.get('balance')
        if (line.get('accounting', False) == 'fiscal'
                or line.get('accounting', False) == 'both'):
            account_dict['amount_colgap'] += line.get('balance')
        return account_dict

    def _get_filter_code_accounts(self, options):
        code_account_from = False
        code_account_to = False
        if (options.get('account_accounts', False)
                and options.get('account_accounts_to', False)):
            account_from_id = self.env['account.account'].browse(
                options.get('account_accounts'))
            account_to_id = self.env[
                'account.account'].browse(options.get('account_accounts_to'))
            code_account_from = account_from_id.code
            code_account_to = account_to_id.code
        return code_account_from, code_account_to

    def _validate_account_list(self, code_account_from, code_account_to, code):
        if (int(code) >= int(code_account_from)
                and int(code) <= int(code_account_to)):
            return True
        return False

    def _estructure_report(self, account, key):
        columns = []
        lines = []
        report = self.env["account.report"]
        account['difference'] = (
            round(account['amount_colgap']-account['amount_niif'], 2))
        columns = [
            {'name': report.format_value(account.get(
                'amount_colgap'), blank_if_zero=True), 'class': 'number',
             'no_format_name': account.get('amount_colgap')},
            {'name': report.format_value(account.get(
                'amount_niif'), blank_if_zero=True), 'class': 'number',
             'no_format_name': account.get('amount_niif')},
            {'name': report.format_value(account.get(
                'difference'), blank_if_zero=True), 'class': 'number',
             'no_format_name': account.get('difference')}
        ]
        lines.append({
            'id': report._get_generic_line_id("account.account", key),
            'name': "{0} {1}".format(
                    account.get('aa_code'), account.get('aa_name')),
            'title_hover': account.get('aa_name'),
            'columns': columns,
            'caret_options': 'account.account',
        })
        return lines

    def _get_account_line_report(self, all_accounts, options):
        lines = []
        report = self.env["account.report"]
        total_niif = 0.0
        total_colgap = 0.0
        total_balance = 0.0

        code_account_from, code_account_to = (
            self._get_filter_code_accounts(options))

        for key, account in all_accounts.items():
            if not code_account_from and not code_account_to:
                lines += self._estructure_report(account, key)
                total_niif += round(account['amount_niif'], 2)
                total_colgap += round(account['amount_colgap'], 2)
                total_balance += round(account['difference'], 2)
            if (code_account_from and code_account_to
                    and self._validate_account_list(
                        code_account_from, code_account_to,
                        account['aa_code'])):
                lines += self._estructure_report(account, key)
                total_niif += round(account['amount_niif'], 2)
                total_colgap += round(account['amount_colgap'], 2)
                total_balance += round(account['difference'], 2)
        if len(lines) > 0:
            lines.append({
                'id': report._get_generic_line_id(None, None, markup='total'),
                'name': _('Total'),
                'class': 'total',
                'columns': [
                    {
                        'name': report.format_value(total_colgap),
                        'class': 'number'
                    },
                    {
                        'name': report.format_value(total_niif),
                        'class': 'number'
                    },
                    {
                        'name': report.format_value(total_balance),
                        'class': 'number'
                    }
                ],
                'level': 1,
            })
        return lines
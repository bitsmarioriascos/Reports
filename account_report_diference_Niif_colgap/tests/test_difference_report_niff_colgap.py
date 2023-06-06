from datetime import datetime, date
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo import Command, fields


class TestAccountDifferenceReportNiifColgap(TransactionCase):

    def setUp(self):
        super(TestAccountDifferenceReportNiifColgap, self).setUp()
        self.account_account = self.env['account.account']
        self.account_journal = self.env['account.journal']
        self.account_move = self.env['account.move']
        self.res_partner = self.env['res.partner']
        self.res_company = self.env['res.company']

        self.niif_colgap_account_report = self.env.ref(
            'account_report_difference_niif_colgap.difference_niif_colgab')
        self.niif_colgap_report = self.env[
            'account.difference.niif.colgap.report.handler']
        self.company = self.res_company.search([])
        self.res_company.create({
            'name': "Test Company"
        })
        self.res_partner = self.res_partner.create({
            'name': "Test Partner",
            'company_id': self.company.id
        })
        self.account_1 = self.account_account.create({
            'name': 'Test Account 1',
            'code': '51236877',
            'company_id': self.company.id
        })
        self.account_2 = self.account_account.create({
            'name': 'Test Account 2',
            'code': '51236883',
            'company_id': self.company.id
        })
        self.account_3 = self.account_account.create({
            'name': 'Test Account 1',
            'code': '51236887',
            'company_id': self.company.id
        })
        self.account_4 = self.account_account.create({
            'name': 'Test Account 2',
            'code': '51236893',
            'company_id': self.company.id
        })
        self.account_5 = self.account_account.create({
            'name': 'Test Account 2',
            'code': '51236895',
            'company_id': self.company.id
        })
        self.journal = self.account_journal.create({
            'name': 'Test Journal',
            'type': 'general',
            'code': 'TSTJ1',
            'accounting': 'fiscal',
            'company_id': self.company.id
        })
        self.journal_1 = self.account_journal.create({
            'name': 'Test Journal 1',
            'type': 'general',
            'code': 'TSTJ2',
            'accounting': "niif",
            'company_id': self.company.id
        })
        move_1 = self.account_move.create({
            'journal_id': self.journal.id,
            'date': date(2021, 3, 9),
            'company_id': self.company.id,
            'line_ids': [(0, 0, {
                'account_id': self.account_1.id,
                'partner_id': self.res_partner.id,
                'journal_id': self.journal.id,
                'credit': 0.0,
                'debit': 1000.0
            }), (0, 0, {
                'account_id': self.account_2.id,
                'partner_id': self.res_partner.id,
                'journal_id': self.journal.id,
                'credit': 1000.0,
                'debit': 0.0
            })]
        })
        move_1.action_post()
        move_2 = self.account_move.create({
            'journal_id': self.journal_1.id,
            'company_id': self.company.id,
            'date': date(2021, 3, 9),
            'line_ids': [(0, 0, {
                'account_id': self.account_3.id,
                'partner_id': self.res_partner.id,
                'journal_id': self.journal_1.id,
                'credit': 0.0,
                'debit': 1000.0
            }), (0, 0, {
                'account_id': self.account_4.id,
                'partner_id': self.res_partner.id,
                'journal_id': self.journal_1.id,
                'credit': 1000.0,
                'debit': 0.0
            })]
        })
        move_2.action_post()
        move_3 = self.account_move.create({
            'journal_id': self.journal_1.id,
            'company_id': self.company.id,
            'date': date(2021, 3, 9),
            'line_ids': [(0, 0, {
                'account_id': self.account_3.id,
                'partner_id': self.res_partner.id,
                'journal_id': self.journal_1.id,
                'credit': 0.0,
                'debit': 1000.0
            }), (0, 0, {
                'account_id': self.account_4.id,
                'partner_id': self.res_partner.id,
                'journal_id': self.journal_1.id,
                'credit': 1000.0,
                'debit': 0.0
            })]
        })
        move_3.action_post()
        move_4 = self.account_move.create({
            'journal_id': self.journal_1.id,
            'company_id': self.company.id,
            'date': date(2021, 3, 9),
            'line_ids': [(0, 0, {
                'account_id': self.account_4.id,
                'partner_id': self.res_partner.id,
                'journal_id': self.journal_1.id,
                'credit': 0.0,
                'debit': 1000.0
            }), (0, 0, {
                'account_id': self.account_5.id,
                'partner_id': self.res_partner.id,
                'journal_id': self.journal_1.id,
                'credit': 1000.0,
                'debit': 0.0
            })]
        })
        move_4.action_post()
        self.options = {
            'account_accounts': self.account_1.id,
            'account_accounts_to': self.account_4.id,
            'date': {
                'date_from': "2021-01-01",
                'date_to': "2021-12-31"
            },
            'journals': [
                {
                    'id': self.journal.id,
                    'name': self.journal.name,
                    'code': self.journal.code,
                    'type': self.journal.type,
                    'selected': True
                }, {
                    'id': self.journal_1.id,
                    'name': self.journal_1.name,
                    'code': self.journal_1.code,
                    'type': self.journal_1.type,
                    'selected': True
                }
            ]
        }

    def test_init_filter_range_account(self):
        self.niif_colgap_account_report._init_options_range_account(
            self.options)

    def test_init_filter_range_not_filter_range_account(self):
        self.niif_colgap_account_report.filter_range_account = True
        self.niif_colgap_account_report._init_options_range_account(
            self.options)

    def test_dynamic_lines_generator(self):
        self.niif_colgap_report._dynamic_lines_generator(
            self.niif_colgap_report, self.options, None)

    def test_dynamic_lines_generator_without_accounts(self):
        self.options['account_accounts'] = False
        self.options['account_accounts_to'] = False
        self.niif_colgap_report._dynamic_lines_generator(
            self.niif_colgap_report, self.options, None)

    def test_dynamic_lines_generator_without_journals(self):
        self.options['journals'] = []
        self.niif_colgap_report._dynamic_lines_generator(
            self.niif_colgap_report, self.options, None)

    def test_dynamic_lines_generator_journals_not_selected(self):
        self.options['journals'] = [
            {
                'id': self.journal.id,
                'name': self.journal.name,
                'code': self.journal.code,
                'type': self.journal.type,
                'selected': False
            }, {
                'id': self.journal_1.id,
                'name': self.journal_1.name,
                'code': self.journal_1.code,
                'type': self.journal_1.type,
                'selected': False
            }
        ]
        self.niif_colgap_report._dynamic_lines_generator(
            self.niif_colgap_report, self.options, None)

    def test_multi_company_odoo(self):
        self.options['multi_company'] = [
            {
                'id': self.res_company.id,
                'name': self.res_company.name,
                'selected': False
            }, {
                'id': self.company.id,
                'name': self.company.name,
                'selected': True
            }
        ]
        self.niif_colgap_report._dynamic_lines_generator(
            self.niif_colgap_report, self.options, None)
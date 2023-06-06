from heapq import merge
from odoo.tests.common import TransactionCase
from odoo.tests import Form
from odoo.tools import date_utils
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools.misc import formatLang
from odoo.addons.account_report_adjustment.tests.common import TestReportCommon
from odoo.addons.account_report_adjustment.controllers.main import ExcelExportI


from odoo.addons.website.tools import MockRequest
from unittest.mock import patch, Mock, MagicMock
import datetime
import copy
from datetime import date

import logging
_logger = logging.getLogger(__name__)

GENERAL_LEDGER = "account.general.ledger"
ZERO_MONETARY = "$ 0,00"


class TestAccountReportAdjustment(TransactionCase):

    def setUp(self):
        super(TestAccountReportAdjustment, self).setUp()

        self.res_company = self.env['res.company']
        self.general_ledger = self.env[GENERAL_LEDGER]
        self.account_journal = self.env['account.journal']
        self.res_partner = self.env['res.partner']
        self.account_account = self.env['account.account']
        self.account_move = self.env['account.move']
        self.company = self.env.ref('base.main_company')
        self.company.country_id = self.env.ref('base.co')
        self.company.template_code = '01'

        self.mar_year_minus_1 = datetime.datetime.strptime(
            '2017-03-01', DEFAULT_SERVER_DATE_FORMAT).date()

        self.journal_id = self.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'general',
            'code': 'TSTJ1',
            'company_id': self.company.id,
            'accounting': 'both'
        })

        self.partner = self.res_partner.create({
            'name': "TST Partner"
        })
        self.account = self.account_account.create({
            'code': "111005",
            'name': "TST Account",
            'user_type_id': (
                self.env.ref('account.data_account_type_liquidity').id),
            'reconcile': True
        })
        self.move = self.account_move.create({
            'name': "/",
            'journal_id': self.journal_id.id,
            'date': date(2020, 7, 22),
            'type': "entry",
            'line_ids': [(0, 0, {
                'account_id': self.account.id,
                'partner_id': self.partner.id,
                'debit': 1000,
                'date_maturity': date(2020, 7, 22),
            }), (0, 0, {
                'account_id': self.account.id,
                'partner_id': self.partner.id,
                'credit': 1000,
                'date_maturity': date(2020, 7, 22),
            })]
        })

        self.lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': '$ 4.794.018.792,74aa', 'class': 'number'},
                    {'name': '$ -43.143.144,39', 'class': 'number'}
                ],
                'level': 2,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': '$ 2.984.486.884,31', 'class': 'number'},
                    {'name': '$ -2.984.486.884,42', 'class': 'number'}
                ],
                'level': 2,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': 'general_ledger_total_1',
                'name': 'Total',
                'class': 'total',
                'level': 1,
                'columns': [
                    {'name': '$ 9.647.791.609,16', 'class': 'number'},
                    {'name': '$ 9.701.198.711,33', 'class': 'number'},
                    {'name': '$ -53.407.102,17', 'class': 'number'}
                ],
                'colspan': 6
            }
        ]

        self.options = {
            'unfolded_lines': [],
            'multi_company': [
                {'id': 4, 'name': 'FONI', 'selected': False},
                {'id': 2, 'name': 'JATECNOLOGY Y CIA', 'selected': False}
            ],
            'date': {
                'mode': 'range',
                'date_from': '2022-01-01',
                'date_to': '2022-06-30'
            },
            'analytic': True,
            'all_entries': False,
            'analytic_accounts': [],
            'selected_analytic_account_names': [],
            'analytic_tags': [],
            'selected_analytic_tag_names': [],
            'hierarchy': False,
            'journals': [
                {"id": self.journal_id.id, "name": self.journal_id.name,
                    'code': self.journal_id.code,
                    'type': 'general', 'selected': False},
                {'id': 'divider', 'name': 'BITS Americas S.A.S.'},
                {'id': 103, 'name': 'AMORTIZACION (Fiscal)',
                    'code': 'AMF', 'type': 'general', 'selected': False},
                {'id': 91, 'name': 'Ajustes Activos Fijos e Intangibles',
                    'code': 'NAFI', 'type': 'general', 'selected': False}
            ],
            'unfold_all': False,
            'unposted_in_period': True
        }
        self.previous_options = {}

    def _init_options(self, report, date_from, date_to):
        report.filter_date = {
            'date_from': date_from.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'date_to': date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
            'filter': 'custom',
            'mode': report.filter_date.get('mode', 'range'),
        }
        return report._get_options(None)

    def test_report_level_1(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': '$ 4.794.018.792,74a', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                'level': 2,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': '$ 2.984.486.884,33', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                "parent_id": "account_16281",
                'level': 3,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        report._change_lines_with_title_0(lines, 1)

    def test_report_level_1_1(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': '$ 4.794.018.792,74aaaa', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                'level': 2,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': '$ 2.984.486.884,34', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                "parent_id": "",
                'level': 3,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        report._change_lines_with_title_0(lines, 1)

    def test_report_level_2(self):
        report = self.env[GENERAL_LEDGER]
        report._change_lines_with_title_0(self.lines, 2)

    def test_report_level_4(self):
        report = self.env[GENERAL_LEDGER]
        report._change_lines_with_title_0(self.lines, 4)

    def test_report_level_5(self):
        report = self.env[GENERAL_LEDGER]
        report._change_lines_with_title_0(self.lines, 5)

    def test_report_level_5_1(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': '$ 4.794.018.792,74aab', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                'level': 2,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': '$ 2.984.486.884,35', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                "parent_id": "account_16281",
                'level': 3,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        report._change_lines_with_title_0(lines, 5)

    def test_report_level_5_2(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': '$ 4.794.018.792,74acd', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                'level': 2,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': '$ 2.984.486.884,36', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                "parent_id": "",
                'level': 3,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        report._change_lines_with_title_0(lines, 5)

    def test_report_record_level_1(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': '$ 4.794.018.792,74asd', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                'level': 2,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': '$ 2.984.486.884,37', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                "parent_id": "account_16281",
                'level': 3,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        report._change_lines_with_record_0(lines, 1)

    def test_report_record_level_1_1(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': '$ 4.794.018.792,74af', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                'level': 4,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': '$ 2.984.486.884,38', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                "parent_id": "",
                'level': 4,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        report._change_lines_with_record_0(lines, 1)

    def test_report_record_level_2(self):
        report = self.env[GENERAL_LEDGER]
        report._change_lines_with_record_0(self.lines, 2)

    def test_report_record_level_1_2(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': '$ 4.794.018.792,74axa', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                'level': 4,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': '$ 2.984.486.884,39', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                "parent_id": "",
                'level': 4,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        report._change_lines_with_record_0(lines, 2)

    def test_report_record_level_3(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': 50, 'class': 'number'},
                    {'name': "", 'class': 'number'}
                ],
                'level': 4,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': "", 'class': 'number'},
                    {'name': "", 'class': 'number'}
                ],
                "parent_id": "",
                'level': 4,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        report._change_lines_with_record_0(lines, 3)

    def test_report_record_level_3_1(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': "", 'class': 'number'}
                ],
                'level': 4,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': 50, 'class': 'number'},
                    {'name': "", 'class': 'number'}
                ],
                "parent_id": "",
                'level': 4,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        report._change_lines_with_record_0(lines, 3)

    def test_report_record_level_3_2(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': "", 'class': 'number'}
                ],
                'level': 4,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': "", 'class': 'number'},
                    {'name': 50, 'class': 'number'}
                ],
                "parent_id": "",
                'level': 4,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        report._change_lines_with_record_0(lines, 3)

    def test_report_record_level_4(self):
        report = self.env[GENERAL_LEDGER]
        report._change_lines_with_record_0(self.lines, 4)

    def test_report_record_level_5(self):
        report = self.env[GENERAL_LEDGER]
        report._change_lines_with_record_0(self.lines, 5)

    def test_report_record_level_5_1(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': '$ 4.794.018.792,74aaa', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                'level': 3,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': '$ 2.984.486.884,40', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                "parent_id": "account_16281",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '6666',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': '$ 2.984.486.884,41', 'class': 'number'},
                    {'name': 50, 'class': 'number'}
                ],
                "parent_id": "account_16281",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
        ]
        report._change_lines_with_record_0(lines, 5)

    def test_report_record_level_5_2(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'},
                    {'name': 50, 'class': 'number'}
                ],
                'level': 4,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', },
                    {'name': '', 'class': 'number'},
                    {'name': ZERO_MONETARY, 'class': 'number'},
                    {'name': 0.0, 'class': 'number'},
                    {'name': 0.0, 'class': 'number'}
                ],
                "parent_id": "",
                'level': 4,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        report._change_lines_with_record_0(lines, 5)

    def test_report_without_columns(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [],
                'level': 4,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': '555',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [],
                "parent_id": "",
                'level': 4,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        ctx = {"active_model": GENERAL_LEDGER}
        report._add_xlsx_column(lines, ctx, self.options)
        self.options["hierarchy"] = True
        report._add_xlsx_column(lines, ctx, self.options)

    def test_report_add_new_column(self):
        report = self.env[GENERAL_LEDGER]
        lines = [
            {
                'id': 'account_16281',
                'name': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'title_hover': '11200503 BANCO DAVIVIENDA CTA AHORROS 05...',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': 0.0, 'class': 'number'},
                    {'name': 50, 'class': 'number'}
                ],
                'level': 4,
                "parent_id": "",
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': 'abc_abc',
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': "", 'class': 'number'},
                    {'name': "", 'class': 'number'}
                ],
                "parent_id": "",
                'level': 4,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            },
            {
                'id': 12345,
                'name': '13050501 CLIENTES NACIONALES',
                'title_hover': '13050501 CLIENTES NACIONALES',
                'columns': [
                    {'name': '', 'class': 'number'},
                    {'name': '', 'class': 'number'},
                    {'name': "", 'class': 'number'},
                    {'name': "", 'class': 'number'}
                ],
                "parent_id": "",
                'level': 4,
                'unfoldable': False,
                'unfolded': None,
                'colspan': 5
            }
        ]
        ctx = {"active_model": GENERAL_LEDGER}
        report._add_xlsx_column(lines, ctx, self.options)
        ctx = {"active_model": 'account.aged.payable'}
        report._add_xlsx_column(lines, ctx, self.options)
        ctx = {"active_model": GENERAL_LEDGER, "hierarchy": True}
        report._add_xlsx_column(lines, ctx, self.options)

    def test_report_record_level_6(self):
        report = self.env[GENERAL_LEDGER]
        report._change_lines_with_record_0(self.lines, 6)

    def test_report(self):
        report = self.env[GENERAL_LEDGER]
        _ = report._get_lines(self.options)
        report.report_type = 1
        report._get_partner_data(self.partner.id, "id")
        self.options["comparison"] = {"filter": "comparison"}
        report.get_xlsx(self.options)

    def test_report_hierarchy(self):
        report = self.env[GENERAL_LEDGER]
        _ = report._get_lines(self.options)
        report.report_type = 1
        report._get_partner_data(self.partner.id, "id")
        self.options["hierarchy"] = True
        report.get_xlsx(self.options)
        report.report_type = 2
        report.get_xlsx(self.options)

    def test_report_change_lines(self):
        report = self.env[GENERAL_LEDGER]
        _ = report._get_lines(self.options)
        report.report_type = 1
        report._change_lines(self.lines, report.report_type)
        report.report_type = 2
        report._change_lines(self.lines, report.report_type)

    def test_account_assets_report(self):
        report = self.env['account.assets.report']
        _ = report._get_lines(self.options)
        report.get_xlsx(self.options)

    def test_account_aged_payable(self):
        report = self.env["account.aged.payable"]
        report.get_xlsx(self.options)

    def test_account_cash_flow_report(self):
        report = self.env["account.cash.flow.report"]
        report._change_lines(self.lines, report.report_type)
        report.get_xlsx(self.options)

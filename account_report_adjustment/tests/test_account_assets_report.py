# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools, fields
from odoo.tests import common
from odoo.modules.module import get_resource_path
from odoo.exceptions import UserError, ValidationError, MissingError
from odoo.tools import float_compare, date_utils
from odoo.tests.common import Form
from odoo.addons.account_reports.tests.common import _init_options


import datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch


def today():
    # 31'st of december is a particular date because entries are configured
    # to be autoposted on that day. The test values dont take it into account
    # so we just mock the date and run the 31'st as if it was the 30'th
    today = fields.Date.today()
    if today.month == 12 and today.day == 31:
        today += relativedelta(day=30)
    return today


ASSET_REPOT = "account.asset"
EXPENSE = "account_asset.a_expense"
CAS = "account_asset.cas"
MISCELLANEOUS = "account_asset.miscellaneous_journal"
ACCOUNT_MOVE = "account.move"
ASSET_MODIFY = "asset.modify"


class TestAccountAsset(common.TransactionCase):

    @patch('odoo.fields.Date.today', return_value=today())
    def setUp(self, today_mock):
        super(TestAccountAsset, self).setUp()
        self.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)
        self._load('account', 'test', 'account_minimal_test.xml')
        today = fields.Date.today()

        self.report = self.env['account.assets.report']

        self.truck = self.env[ASSET_REPOT].create({
            'account_asset_id': self.env.ref(
                EXPENSE).id,
            'account_depreciation_id': self.env.ref(
                EXPENSE).id,
            'account_depreciation_expense_id': self.env.ref(
                CAS).id,
            'journal_id': self.env.ref(
                MISCELLANEOUS).id,
            'asset_type': 'purchase',
            'name': 'truck',
            'acquisition_date': today + relativedelta(
                years=-6, month=1, day=1),
            'original_value': 10000,
            'salvage_value': 2500,
            'method_number': 10,
            'method_period': '12',
            'method': 'linear',
        })
        self.truck.validate()
        self.env[ACCOUNT_MOVE]._autopost_draft_entries()
        self.assert_counterpart_account_id = self.env.ref(
            'account_asset.a_sale').id

    def _load(self, module, *args):
        tools.convert_file(
            self.cr, 'account_asset',
            get_resource_path(module, *args),
            {}, 'init', False,
            'test', self.registry._assertion_report
        )

    def update_form_values(self, asset_form):
        for i in range(len(asset_form.depreciation_move_ids)):
            with asset_form.depreciation_move_ids.edit(i) as line_edit:
                line_edit.asset_remaining_value

    @patch('odoo.fields.Date.today', return_value=today())
    def test_asset_modify_report(self, today_mock):

        today = fields.Date.today()
        report = self.report

        self.env[ASSET_MODIFY].create({
            'name': 'New beautiful sticker 1',
            'asset_id': self.truck.id,
            'value_residual': 4000,
            'salvage_value': 3000,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        options = _init_options(
            report, today + relativedelta(years=-6, month=1, day=1),
            today + relativedelta(years=+4, month=12, day=31)
        )
        _ = report._get_lines(
            {**options, **{'unfold_all': False, 'all_entries': True}}
        )

    @patch('odoo.fields.Date.today', return_value=today())
    def test_get_header(self, today_mock):
        today = fields.Date.today()
        report = self.report

        options = _init_options(
            report, today + relativedelta(years=-6, month=1, day=1),
            today + relativedelta(years=+4, month=12, day=31)
        )
        _ = report.get_header(options)

    @patch('odoo.fields.Date.today', return_value=today())
    def test_asset_method_degressive(self, today_mock):
        today = fields.Date.today()
        report = self.report

        truck = self.env[ASSET_REPOT].create({
            'account_asset_id': self.env.ref(
                EXPENSE).id,
            'account_depreciation_id': self.env.ref(
                EXPENSE).id,
            'account_depreciation_expense_id': self.env.ref(
                CAS).id,
            'journal_id': self.env.ref(
                MISCELLANEOUS).id,
            'asset_type': 'purchase',
            'name': 'truck',
            'acquisition_date': today + relativedelta(
                years=-6, month=1, day=1),
            'original_value': 10000,
            'salvage_value': 2500,
            'method_period': '12',
            'method': 'degressive',
        })
        truck.validate()
        self.env[ACCOUNT_MOVE]._autopost_draft_entries()

        self.env[ASSET_MODIFY].create({
            'name': 'New beautiful sticker 2',
            'asset_id': truck.id,
            'value_residual': 4000,
            'salvage_value': 3000,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        options = _init_options(
            report, today + relativedelta(years=-6, month=1, day=1),
            today + relativedelta(years=+4, month=12, day=31)
        )
        _ = report._get_lines(
            {**options, **{'unfold_all': False, 'all_entries': True}}
        )

    @patch('odoo.fields.Date.today', return_value=today())
    def test_asset_method_linear(self, today_mock):
        today = fields.Date.today()
        report = self.report

        truck = self.env[ASSET_REPOT].create({
            'account_asset_id': self.env.ref(
                EXPENSE).id,
            'account_depreciation_id': self.env.ref(
                EXPENSE).id,
            'account_depreciation_expense_id': self.env.ref(
                CAS).id,
            'journal_id': self.env.ref(
                MISCELLANEOUS).id,
            'asset_type': 'purchase',
            'name': (
                'This is a character length test, '
                'exceeding 50 in length'),
            'acquisition_date': today + relativedelta(
                years=-6, month=1, day=1),
            'original_value': 10000,
            'salvage_value': 2500,
            'method': 'linear',
        })
        truck.validate()
        self.env[ACCOUNT_MOVE]._autopost_draft_entries()
        self.env[ASSET_MODIFY].create({
            'name': 'New beautiful sticker 3',
            'asset_id': truck.id,
            'value_residual': 4000,
            'salvage_value': 3000,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        options = _init_options(
            report, today + relativedelta(years=-6, month=1, day=1),
            today + relativedelta(years=+4, month=12, day=31)
        )
        _ = report._get_lines(
            {**options, **{'unfold_all': False, 'all_entries': True}}
        )

    @patch('odoo.fields.Date.today', return_value=today())
    def test_asset_closed(self, today_mock):
        today = fields.Date.today()
        report = self.report

        truck = self.env[ASSET_REPOT].create({
            'account_asset_id': self.env.ref(
                EXPENSE).id,
            'account_depreciation_id': self.env.ref(
                EXPENSE).id,
            'account_depreciation_expense_id': self.env.ref(
                CAS).id,
            'journal_id': self.env.ref(
                MISCELLANEOUS).id,
            'asset_type': 'purchase',
            'name': 'truck',
            'acquisition_date': today + relativedelta(
                years=-6, month=1, day=1),
            'original_value': 10000,
            'salvage_value': 2500,
            'method_number': 10,
            'method_period': '12',
            'method': 'linear',
        })
        truck.validate()
        self.env[ACCOUNT_MOVE]._autopost_draft_entries()
        self.env[ASSET_MODIFY].create({
            'name': 'New beautiful sticker 4',
            'asset_id': truck.id,
            'value_residual': 4000,
            'salvage_value': 3000,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        truck.write({"state": "close"})

        options = _init_options(
            report, today + relativedelta(years=-6, month=1, day=1),
            today + relativedelta(years=+4, month=12, day=31)
        )
        _ = report._get_lines(
            {**options, **{'unfold_all': False, 'all_entries': True}}
        )

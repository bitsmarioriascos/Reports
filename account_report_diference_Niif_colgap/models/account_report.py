import json

from odoo import models, _, fields
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import format_date, get_lang

from datetime import timedelta
from collections import defaultdict


class AccountReport(models.Model):
    _inherit = 'account.report'

    filter_range_account = fields.Boolean(
        'Range Account',
        default=False
    )

    def _init_options_range_account(self, options, previous_options=None):
        if 'filter_range_account' in self and not self['filter_range_account']:
            return

        # Account_accounts
        model_account = "account.account"
        options['range_account'] = self.filter_range_account
        options['account_accounts'] = (
            previous_options and previous_options.get(
                'account_accounts') or [])
        account_accounts_ids = options['account_accounts']
        selected_account_accounts = (
            account_accounts_ids
            and self.env[model_account
                         ].browse(account_accounts_ids)
            or self.env[model_account])
        options['selected_account_account_names'] = (
            selected_account_accounts.mapped('name'))
        # Account_accounts_to
        options['account_accounts_to'] = (
            previous_options and previous_options.get(
                'account_accounts_to') or [])
        account_to_ids = options['account_accounts_to']
        selected_account_accounts_to = (
            account_to_ids
            and self.env[model_account
                         ].browse(account_to_ids)
            or self.env[model_account])
        options['selected_account_account_names_to'] = (
            selected_account_accounts_to.mapped('name'))
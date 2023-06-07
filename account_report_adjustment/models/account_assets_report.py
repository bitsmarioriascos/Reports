# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import format_date
from itertools import groupby
from collections import defaultdict

MAX_NAME_LENGTH = 50


class AssetsReport(models.AbstractModel):
    _inherit = 'account.asset.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options)

        for subheader in options['custom_columns_subheaders']:
            if subheader['name'] == _("Characteristics"):
                subheader['colspan'] = 5
                break



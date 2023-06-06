# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang, xlsxwriter


class L10nCoReportsCertificationReportIca(models.AbstractModel):
    _inherit = 'l10n_co_reports.certification_report.ica'
    zero_validation = False
    report_type = 1


class L10nCoReportsCertificationReportIva(models.AbstractModel):
    _inherit = 'l10n_co_reports.certification_report.iva'
    zero_validation = False
    report_type = 1


class L10nCoReportsCertificationReportFuente(models.AbstractModel):
    _inherit = 'l10n_co_reports.certification_report.fuente'
    zero_validation = False
    report_type = 1

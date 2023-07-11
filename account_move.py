# coding: utf-8
import io
import xml.dom.minidom
import zipfile
import pytz
import qrcode
import requests
from functools import partial
from itertools import groupby
from odoo.tools.misc import formatLang, get_lang

from collections import defaultdict
from os import listdir

from datetime import date
from datetime import datetime, timedelta
import base64
from io import BytesIO

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_TIME_FORMAT
from odoo.tools.float_utils import float_compare
from odoo.tools import float_round, date_utils

from odoo.addons.l10n_co_generate_e_invoicing.models.browsable_object \
    import BrowsableObject, Invoive

from odoo.addons.bits_api_connect.models.adapters.builder_file_adapter\
    import BuilderToFile

from odoo.addons.bits_api_connect.models.connections.api_connection\
    import ApiConnectionException

from odoo.addons.bits_api_connect.models.api_connection\
    import ApiConnection

import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    # Python Code
    # TODO Sin prueba unitaria
    def _get_base_local_dict(self):
        return {
            'float_round': float_round
        }

    # TODO Sin prueba unitaria

    def generate_dict_invoice_dian(self):

        def _generate_lines(localdict, line_ids):
            res = []
            for line in line_ids:
                if line.act_field_id and not line.act_field_id\
                   ._satisfy_condition(localdict):
                    continue
                if line.act_field_id:
                    line.act_field_id.validate_required_field(localdict)
                row = dict()
                row['head'] = line.code
                row['lines'] = []
                if line.act_field_id \
                   and line.act_field_id._compute_rule(localdict):
                    headers = line.act_field_id._compute_rule(localdict)
                    for head in headers:
                        localdict['record'] = head
                        row['lines'].append(_generate_children(
                            localdict, line.children_ids))
                else:
                    row['lines'] = _generate_children(
                        localdict, line.children_ids)
                res.append(row)
            return res

        def _generate_children(localdict, children_ids):
            lines = []
            for field_line in children_ids:
                rule = field_line.act_field_id
                if rule and not rule._satisfy_condition(localdict):
                    continue
                rule.validate_required_field(localdict)
                if field_line.children_ids:
                    row = dict()
                    row['head'] = field_line.code
                    row['lines'] = []
                    if rule and rule._compute_rule(localdict):
                        head = rule._compute_rule(localdict)
                        if not isinstance(head, list):
                            row['lines'] = _generate_children(
                                localdict, field_line.children_ids)
                            lines.append(row)
                        else:
                            for head_line in head:
                                localdict['record_1'] = head_line
                                lines.append({
                                    'head': field_line.code,
                                    'lines': _generate_children(
                                        localdict, field_line.children_ids)
                                })
                        continue
                value = ''
                rule = field_line.act_field_id
                compute_rule = rule._compute_rule(localdict)
                if compute_rule:
                    value = compute_rule
                elif not isinstance(compute_rule, bool):
                    value = compute_rule

                line_row = {
                    'label': field_line.name,
                    'code': field_line.code,
                    'value': value,
                    'type': type(value),
                }
                lines.append(line_row)
            return lines
        partner_id = self.partner_id
        localdict = {
            **self._get_base_local_dict(),
            **{
                'account': Invoive(partner_id.id, self, self.env),
                'partner': partner_id,
                'company': self.company_id.partner_id,
            }
        }
        provider = self._get_active_tech_provider()
        res = _generate_lines(localdict, provider.line_ids)
        return res

    def _get_tax_by_group(self, group, index=1):
        for line in self.amount_by_group:
            if line[0] and line[0] == group:
                return line[index]
        return 0.0

    # TODO Sin prueba unitaria
    def _get_total_type_retention(self):
        res = self._get_dict_by_group(retention=True)
        if not len(res):
            return -1
        result = sum([abs(line['amount']) for line in res])
        return result

    def _get_total_type_transferred(self):
        res = self._get_dict_by_group(retention=False)
        if not len(res):
            return -1
        result = sum([abs(line['amount']) for line in res])
        return result
    # TODO Sin prueba unitaria

    def _get_total_type_by_code(self, code):
        res = self._get_dict_by_group()
        result = sum([abs(line['amount']) for line in res
                      if line['code'] == code])
        return result

    def _get_zero_taxes(self):
        self.ensure_one()
        res = {}
        done_taxes = set()
        for line in self.invoice_line_ids:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(
                price_unit, quantity=line.quantity, currency=line.currency_id,
                product=line.product_id, partner=line.partner_id
            )
            for tax in taxes['taxes']:
                if tax['amount'] == 0:
                    tax_line_id = self.env['account.tax'].browse(tax['id'])
                    res.setdefault(
                        tax_line_id.id,
                        {
                            'base': 0.0,
                            'amount': 0.0,
                            'rate': tax_line_id.amount,
                            'code': tax_line_id.type_of_tax.code,
                            'name': tax_line_id.type_of_tax.name,
                            'retention': tax_line_id.type_of_tax.retention
                        }
                    )

                    res[tax_line_id.id]['amount'] += tax['amount']
                    res[tax_line_id.id]['base'] += tax['base']
        return res

    def _get_dict_by_group(self, retention=None):
        self.ensure_one()
        lang_env = self.with_context(lang=self.partner_id.lang).env
        tax_lines = self.line_ids.filtered(
            lambda line: line.tax_line_id and
            line.tax_line_id.tax_group_fe != 'nap_fe')
        res = self._get_zero_taxes()
        done_taxes = set()
        for line in tax_lines:
            res.setdefault(
                line.tax_line_id.id,
                {
                    'base': 0.0,
                    'amount': 0.0,
                    'rate': line.tax_line_id.amount,
                    'code': line.tax_line_id.type_of_tax.code,
                    'name': line.tax_line_id.type_of_tax.name,
                    'retention': line.tax_line_id.type_of_tax.retention,
                    'description': line.tax_line_id.description
                }

            )
            res[line.tax_line_id.id]['amount'] += line.price_subtotal
            tax_key_add_base = tuple(
                self._get_tax_key_for_group_add_base(line))
            if tax_key_add_base not in done_taxes:
                if line.currency_id != self.company_id.currency_id:
                    amount = self.company_id.currency_id._convert(
                        line.tax_base_amount, line.currency_id,
                        self.company_id, line.date or fields.Date.today()
                    )
                else:
                    amount = line.tax_base_amount
                res[line.tax_line_id.id]['base'] += amount
                done_taxes.add(tax_key_add_base)
        if retention is None:
            return [res[k] for k in res]
        result = [res[k] for k in res if res[k]['retention'] == retention]
        return result

    def action_test(self):
        pass
    # TODO Sin prueba unitaria

    def action_test_api_connect(self):
        provider = self._get_active_tech_provider()
        url = provider.url_download or ''
        request = self._create_api_conection(provider=provider, url=url)
        for record in self:
            if not record.ei_number or not record.type:
                raise ValidationError(
                    _(
                        'This invoice does not have the'
                        '"ei_number" or "type" attribute'
                    )
                )
            response, result, exception = request.download(
                record.type,
                record.ei_number
            )
            api_resp = result.get('response', False)
            if not api_resp or \
               not api_resp.get('representacionGrafica', False) or exception:
                record.message_post(
                    body=_(
                        'An error occurred during the request'
                    )
                )
                continue
            filename = record.ei_number + '.pdf'
            graph_src = api_resp.get('representacionGrafica')
            if not isinstance(graph_src, bytes):
                _file = BytesIO(base64.b64decode(graph_src))
                _file.seek(0)
                graph_src = _file.read()
            record.message_post(
                body=_(
                    'Correct operation of the query to ' +
                    'the asynchronous web service'
                ),
                attachments=[(filename, graph_src)]
            )
            record.write({
                'ei_pdf_base64_bytes': base64.encodestring(graph_src),
                'ei_file_name': filename,
            })

    def _upload_message_electronic_invoice(self):
        for invoice in self:
            invoice.message_post(
                body=_('Electronic invoice submission.<br/>'),
            )
    # TODO Sin prueba unitaria

    def _generate_file(self):
        data = self.generate_dict_invoice_dian()
        provider = self._get_active_tech_provider()

        file = BuilderToFile.prepare_file_for_submission(
            provider.file_extension,
            provider.file_adapter, data,
            provider.file_separator
        )
        return file

    @api.model
    def _create_api_conection(self, provider=None, url=None):
        tech_provider = (
            self._get_active_tech_provider()
            if not provider else provider
        )
        if not url:
            url = provider.url_upload or ''
        result = ApiConnection.prepare_connection(tech_provider, url)
        return result
    # TODO Sin prueba unitaria

    def _generate_electronic_invoice_tech_provider(self, attachments=False):
        provider = self._get_active_tech_provider()
        try:
            request = self._create_api_conection(provider=provider)
            filename = 'archivo_enviado_pt.txt'
            file = self._generate_file()
        except requests.exceptions.ConnectionError as e:
            self.l10n_co_log_rejected_invoice_connection(e)
        response = request.upload(
            self._get_ei_type_dian(), filename, file, attachments
        )
        if response:
            self.finish_send_dian(response, attachments, filename, file)
        else:
            self.l10n_co_log_rejected_invoice("error", filename, file)
    # TODO Sin prueba unitaria

    def finish_send_dian(self, response, attachments, filename, file):
        error_msg = response.get('error_msg', '')
        status = response.get('status', '')
        descripcion = response['descripcion'] \
            if response.get('descripcion', False) else ''
        cufe = response['cufe'] if response.get('cufe', False) else ''
        transaccionID = response['transaccionID'] \
            if response.get('transaccionID', False) else ''
        numeroDocumento = response['numeroDocumento'] \
            if response.get('numeroDocumento', False) else ''
        cadenaQR = response['cadenaQR'] \
            if response.get('cadenaQR', False) else ''
        with self.pool.cursor() as cr:
            attachment = self.env['ir.attachment'].create({
                'name': transaccionID+filename,
                'datas': base64.b64encode(file),
                'res_model': self._name,
                'type': 'binary',
                'res_id': self.id
            })
            self.message_post(
                body=_('CUDE/CUFE: %s<br/>Transaction No: %s<br/>'
                       'No Document: %s<br/>Description: %s<br/>') %
                (cufe, transaccionID, numeroDocumento, descripcion))
            self.invoice_status = status
            self.cufe_cude_ref = cufe
            self.ei_number = transaccionID
            self.ei_qr_data = cadenaQR
    # TODO Sin prueba unitaria

    def _validate_account_move_type(self):
        self.ensure_one()
        return self.move_type in ('out_invoice', 'out_refund')
    # TODO Sin prueba unitaria

    def _validate_sequence_dian(self):
        self.ensure_one()
        sequence = self._get_last_sequence()
        move_sequence = self.env['ir.sequence'].search(
            [('code', '=', 'FE'),
             ('company_id', 'in', [self.company_id.id, False])], order='company_id', limit=1)
        return (move_sequence.use_dian_control
                and move_sequence.dian_type == 'computer_generated_invoice')
    # TODO Sin prueba unitaria

    def post_dian_invoice(self):
        _now = fields.Datetime.now().replace(second=0)
        for move in self:
            if not move.invoice_date and move.is_sale_document():
                _date = move.ei_invoice_datetime.replace(second=0) \
                    if move.ei_invoice_datetime else _now
                move.invoice_date = _date.strftime('%Y-%m-%d')
                move.ei_invoice_datetime = _date
                move.with_context(check_move_validity=False)\
                    ._onchange_invoice_date()
        res = True
        if not self.company_id.active_tech_provider:
            return res

        recs_invoice = self.filtered(lambda x: x.is_sale_document())
        for invoice in recs_invoice:
            if invoice.company_id.tax_group_id:
                invoice.validate_required_tax()
            if invoice.move_type == 'out_refund' and not invoice.ei_origin_id:
                raise UserError(
                    _('You need to add a document reference before posting.')
                )
            today = pytz.utc.localize(_now)
            bogota_tz = pytz.timezone('America/Bogota')
            today = today.astimezone(bogota_tz)
            if (invoice.currency_id.id != invoice.company_currency_id.id and
                    invoice.currency_id.date != today.date()):
                raise UserError(
                    _('You need to set the TRM of the day.')
                )
            _lang = invoice.partner_id.lang or 'es_ES'
            ei_amount_text = invoice.ei_amount_text \
                if invoice.ei_amount_text \
                else invoice.currency_id.with_context(lang=_lang)\
                .amount_to_text(invoice.amount_total)
            sequence = invoice._get_last_sequence()
            sequence_date = invoice.date or invoice.invoice_date
            invoice_sequence = self.env['ir.sequence'].search(
                [('code', '=', 'FE'),
                 ('company_id', 'in', [self.company_id.id, False])], order='company_id', limit=1)
            prefix, dummy = invoice_sequence._get_prefix_suffix(
                date=sequence_date, date_range=sequence_date)
            number_next = invoice.name.replace(prefix, "")

            to_write = {
                'ei_serie': prefix,
                'ei_folio': number_next,
                'ei_amount_text': ei_amount_text
            }
            invoice.write(to_write)
            for line in invoice.advances_line_ids:
                invoice.js_assign_outstanding_line(line.id)

        provider = self._get_active_tech_provider()
        if not provider:
            raise UserError(
                _('Please configure technology provider '
                  'for electronic invoicing')
            )
        to_process = self.filtered(
            lambda move: move._validate_account_move_type()
            and move._validate_sequence_dian())
        if to_process:
            to_process._generate_electronic_invoice_tech_provider(
                self.attachments
            )

        return res
    # TODO Sin prueba unitaria

    def send_dian(self, invoices=[]):
        if not invoices:
            invoice = self.filtered(
                lambda x: x.invoice_status != "accepted" and x.state == "posted")
        else:
            invoice = invoices
        for rec in invoice:
            if self.env.user.user_has_groups('l10n_co_generate_e_invoicing.group_send_dian') or self.env.uid == 1:
                try:
                    rec.post_dian_invoice()
                    rec.update({"ei_errors_messages": ""})
                except Exception as e:
                    rec.write({"ei_errors_messages": e})
            else:
                raise UserError(
                    _('you do not have permissions, contact the administrator')
                )
    # TODO Sin prueba unitaria

    def send_massive_invoices_dian(self):
        valid_invoices = self.env['account.move'].search([
            ('invoice_status', '=', 'not_sent'),
            ('state', '=', 'posted')
        ])
        self.send_dian(valid_invoices)
    # TODO Sin prueba unitaria

    def get_category_to_apply(self):
        buyer_tx_liability = self.partner_id.fiscal_responsibility
        seller_tx_liability = self.company_id.partner_id.fiscal_responsibility
        lines = seller_tx_liability.line_ids.filtered(
            lambda line: line.fiscal_responsability_id == buyer_tx_liability)
        return lines.applicable_tax

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        super(AccountInvoice, self)._onchange_partner_id()
        for line in self.invoice_line_ids:
            line.tax_ids = line._get_computed_taxes()

    def _get_surchange_discount_data(self):
        return super(AccountInvoice, self)._get_surchange_discount_data()

    def action_cron_get_document_invoices(self):
        date_act = fields.Datetime.now()
        last_notif_mail = fields.Datetime.to_string(
            self.env.context.get('lastcall') or date_act)
        invoices = self.env['account.move'].search([
            ('ei_number', '!=', False),
            ('invoice_status', '=', 'accepted'),
            ('ei_pdf_base64_bytes', '=', False),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ])
        if len(invoices) == 0:
            return
        provider = self._get_active_tech_provider()
        tech_provider_request = ApiConnection.prepare_connection(provider)
        for invoice in invoices:
            response, result, exception = tech_provider_request.download(
                invoice._get_ei_type_dian(),
                invoice.ei_number
            )
            api_resp = result.get('response', False)
            if not api_resp or \
               not api_resp.get('representacionGrafica', False) or exception:
                invoice.message_post(
                    body=_(
                        'An error occurred during the request'
                    )
                )
                continue
            filename = invoice.ei_number + '.pdf'
            filename2 = invoice.ei_number + '.xml'
            graph_src = api_resp.get('representacionGrafica')
            if graph_src is not None and not isinstance(graph_src, bytes):
                _file = BytesIO(base64.b64decode(graph_src))
                _file.seek(0)
                graph_src = _file.read()
            invoice.message_post(
                body=_(
                    'Correct operation of the query to ' +
                    'the asynchronous web service'
                ),
                attachments=[(filename, graph_src)]
            )
            app_resp_doc = api_resp.get(
                'representacionGraficaAppResponse', False)
            if app_resp_doc is not None and \
               not isinstance(app_resp_doc, bytes):
                _file = BytesIO(base64.b64decode(app_resp_doc))
                _file.seek(0)
                app_resp_doc = _file.read()

            app_resp = api_resp.get('appResponse', False)
            if app_resp is not None and not isinstance(app_resp, bytes):
                _file = BytesIO(base64.b64decode(app_resp))
                _file.seek(0)
                app_resp = _file.read()

            dian_ubl = api_resp.get('ubl', False)
            if dian_ubl is not None and not isinstance(dian_ubl, bytes):
                _file = BytesIO(base64.b64decode(dian_ubl))
                _file.seek(0)
                dian_ubl = _file.read()

            base64_1 = base64.encodestring(app_resp) if\
                isinstance(app_resp, bytes) else False
            base64_2 = base64.encodestring(dian_ubl) if\
                isinstance(dian_ubl, bytes) else False
            base64_3 = base64.encodestring(app_resp_doc) if\
                isinstance(app_resp_doc, bytes) else False
            base64_4 = base64.encodestring(graph_src) if\
                isinstance(graph_src, bytes) else False

            invoice.write({
                'ei_app_resp_file_name': 'app_resp_' + filename2,
                'ei_application_response_base64_bytes': base64_1,
                'ei_dian_resp_file_name': 'ubl_' + filename2,
                'ei_dian_response_base64_bytes': base64_2,
                'ei_dian_document_file_name': 'comprobante_dian_' + filename,
                'ei_attached_document_base64_bytes': base64_3,
                'ei_file_name': filename,
                'ei_pdf_base64_bytes': base64_4,
                'ei_status_code': api_resp.get('codigo', ''),
                'ei_status_description': api_resp.get('descripcion', ''),
                'ei_status_message': api_resp.get('estatusDocumento', ''),
            })

    def action_post_with_files(self):
        self.ensure_one()
        if (
            self.move_type in ['out_invoice', 'out_refund'] and
            self._get_active_tech_provider()
        ):
            compose_form = self.env.ref(
                'l10n_co_generate_e_invoicing.support_files_send_wizard_form',
                raise_if_not_found=False
            )
            provider = self._get_active_tech_provider()
            ctx = dict(
                message=_(
                    'For the technology provider %s '
                    'the number of support files is: %s'
                    % (provider.name, provider.num_doc_attachs)
                ),
                invoice_id=self.id,
            )
            return {
                'name': _('Send Support Filess'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'support.files.send',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }
        else:
            raise ValidationError(
                _(
                    'There is no technology provider configured'
                )
            )

    def _action_post_files(self, attachments, reconcile_line_ids,
                           note='', extra_refs=False):
        self.ensure_one()
        # self.attachments = attachments
        self.ei_ubl_note = note
        self.advances_line_ids = reconcile_line_ids
        self.extra_ref_ids = extra_refs \
            if extra_refs and len(extra_refs) > 0 else False
        super(AccountInvoice, self).action_post()
        if attachments:
            attachments_message = list()
            for attach in attachments:
                attachments_message.append(
                    (attach.name, base64.b64decode(attach.datas))
                )
            self.message_post(
                body=_('These are the support files that are attached<br/>'),
                attachments=attachments_message
            )

    def l10n_co_log_rejected_invoice(self, descripcion, filename, file):
        if not self._context.get('not_auto_commit', False):
            self.env.cr.rollback()
        descripcion = descripcion if isinstance(descripcion, str) else ""
        with self.pool.cursor() as cr:
            self.with_env(self.env(cr=cr, user=SUPERUSER_ID)).message_post(
                body=_('Connection error:<br/>%s') % descripcion,
                attachments=[(filename, file)])
            self.with_env(self.env(cr=cr, user=SUPERUSER_ID)).write({
                'invoice_status': 'rejected'})
        raise UserError(_(
            'The document has been rejected by DIAN. For '
            'more information, please contact the '
            'administrator.\nError: %s' % (descripcion.replace("<br/>", "\n"))
        ))

    def _get_ei_type_dian(self):
        _ref = 'l10n_co_account_e_invoice.l10n_co_type_documents_'
        if (
            self.move_type == 'out_invoice' and
            self.ei_type_document_id.id != self.env.ref(_ref + '6').id
        ):
            return self.move_type
        return 'out_refund_credit'\
            if self.ei_type_document_id.id == self.env.ref(_ref + '5').id\
            else 'out_refund_debit'

    def action_cron_get_acceptance_status(self):
        date_act = fields.Datetime.now()
        last_notif_mail = fields.Datetime.to_string(
            self.env.context.get('lastcall') or date_act)
        invoices = self.env['account.move'].search([
            ('status_inquiry_deadline', '>=', date_act),
            ('invoice_status', '=', 'accepted'),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ])
        if len(invoices) == 0:
            return
        provider = self._get_active_tech_provider()
        tech_provider_request = ApiConnection.prepare_connection(provider)
        for invoice in invoices:
            invoice_status = tech_provider_request.validate_status(
                invoice.type,
                invoice.ei_number
            )
            if not invoice_status:
                continue
            if invoice_status != invoice.ei_status_message:
                invoice.message_post(
                    body=_(
                        'The acceptance status of the invoice'
                        'changed from %s to %s' % (
                            invoice.ei_status_message
                            if invoice.ei_status_message else "''",
                            invoice_status
                        )
                    )
                )
            invoice.write({
                'ei_status_message': invoice_status,
            })

    def validate_final_acceptance_status(self):
        date_act = fields.Datetime.now()
        last_notif_mail = fields.Datetime.to_string(
            self.env.context.get('lastcall') or date_act)
        invoices = self.env['account.move'].search([
            ('status_inquiry_deadline', '<', date_act),
            ('invoice_status', '=', 'accepted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('ei_status_message', '!=', 'Aceptada')
        ])
        if len(invoices) == 0:
            return
        for invoice in invoices:
            if (
                invoice.ei_status_message == 'Enviado a Adquiriente' or
                invoice.ei_status_message == 'Fiscalmente Valido' or
                invoice.ei_status_message == ''
            ):
                invoice.ei_status_message = 'Aceptada'
                invoice.message_post(
                    body=_(
                        'The acceptance deadline is over, which is why the'
                        ' invoice status is "Accepted"'
                    )
                )
    # TODO Sin prueba unitaria

    def l10n_co_log_rejected_invoice_connection(self, descripcion):
        if not self._context.get('not_auto_commit', False):
            self.env.cr.rollback()
        with self.pool.cursor() as cr:
            self.with_env(self.env(cr=cr, user=SUPERUSER_ID)).message_post(
                body=_('Connection error:<br/>%s') % descripcion)
            self.with_env(self.env(cr=cr, user=SUPERUSER_ID)).write({
                'invoice_status': 'rejected'})
        raise UserError(_(
            'The connection is down '
            'more information, please contact the '
            'administrator.\nError: %s' % descripcion
        ))

    def validate_required_tax(self):
        self.ensure_one()
        group = self.company_id.tax_group_id
        for line in self.invoice_line_ids:
            iva = line._get_data_taxes_e_invoice_line(group.name)
            if len(iva) == 0:
                raise UserError(
                    _('You need to add a Iva taxes before posting.')
                )

    def _get_reconciled_info_JSON_values(self):
        for move in self:
            payments_widget_vals = {'title': _(
                'Less Payment'), 'outstanding': False, 'content': []}

            if move.state == 'posted' and move.is_invoice(include_receipts=True):
                reconciled_vals = []
                reconciled_partials = move._get_all_reconciled_invoice_partials()
                for reconciled_partial in reconciled_partials:
                    counterpart_line = reconciled_partial['aml']
                    if counterpart_line.move_id.ref:
                        reconciliation_ref = '%s (%s)' % (
                            counterpart_line.move_id.name, counterpart_line.move_id.ref)
                    else:
                        reconciliation_ref = counterpart_line.move_id.name
                    if counterpart_line.amount_currency and counterpart_line.currency_id != counterpart_line.company_id.currency_id:
                        foreign_currency = counterpart_line.currency_id
                    else:
                        foreign_currency = False

                    reconciled_vals.append({
                        'name': counterpart_line.name,
                        'journal_name': counterpart_line.journal_id.name,
                        'amount': reconciled_partial['amount'],
                        'currency_id': move.company_id.currency_id.id if reconciled_partial['is_exchange'] else reconciled_partial['currency'].id,
                        'date': counterpart_line.date,
                        'partial_id': reconciled_partial['partial_id'],
                        'account_payment_id': counterpart_line.payment_id.id,
                        'payment_method_name': counterpart_line.payment_id.payment_method_line_id.name,
                        'move_id': counterpart_line.move_id.id,
                        'ref': reconciliation_ref,
                        # these are necessary for the views to change depending on the values
                        'is_exchange': reconciled_partial['is_exchange'],
                        'amount_company_currency': formatLang(self.env, abs(counterpart_line.balance), currency_obj=counterpart_line.company_id.currency_id),
                        'amount_foreign_currency': foreign_currency and formatLang(self.env, abs(counterpart_line.amount_currency), currency_obj=foreign_currency)
                    })
                return reconciled_vals

    def _get_advance_values(self):
        self.ensure_one()
        reconciled_vals = self._get_reconciled_info_JSON_values()
        for line in reconciled_vals:
            payment_id = self.env['account.payment'].browse(
                line['account_payment_id'])
            line.update({
                'currency_code': payment_id.currency_id.name
            })
        return reconciled_vals

    def _get_total_advance(self):
        self.ensure_one()
        res = self._get_reconciled_info_JSON_values()
        result = sum([abs(line['amount']) for line in res])
        return result

odoo.define('account_report_difference_niif_colgap.accounts_report', function (require) {
    "use strict";

    var core = require('web.core');
    var accountReportsWidget = require('account_reports.account_report');
    var StandaloneFieldManagerMixin = require(
        'web.StandaloneFieldManagerMixin');
    var RelationalFields = require('web.relational_fields');
    var Widget = require('web.Widget');
    var QWeb = core.qweb;
    var _t = core._t;

    var M2MFilters = Widget.extend(StandaloneFieldManagerMixin, {
        init: function (parent, fields, change_event) {
            this._super.apply(this, arguments);
            StandaloneFieldManagerMixin.init.call(this);
            this.fields = fields;
            this.widgets = {};
            this.change_event = change_event;
        },
        willStart: function () {
            var self = this;
            var defs = [this._super.apply(this, arguments)];
            _.each(this.fields, function (field, fieldName) {
                defs.push(self._makeM2MWidget(field, fieldName));
            });
            return Promise.all(defs);
        },
        start: function () {
            var self = this;
            var $content = $(QWeb.render("m2mWidgetTable", { fields: this.fields }));
            self.$el.append($content);
            _.each(this.fields, function (field, fieldName) {
                self.widgets[fieldName].appendTo($content.find('#' + fieldName + '_field'));
            });
            return this._super.apply(this, arguments);
        },
        _confirmChange: function () {
            var self = this;
            var result = StandaloneFieldManagerMixin._confirmChange.apply(this, arguments);
            var data = {};
            _.each(this.fields, function (filter, fieldName) {
                data[fieldName] = self.widgets[fieldName].value.res_ids;
            });
            this.trigger_up(this.change_event, data);
            return result;
        },
        _makeM2MWidget: function (fieldInfo, fieldName) {
            var self = this;
            var options = {};
            options[fieldName] = {
                options: {
                    no_create_edit: true,
                    no_create: true,
                }
            };
            return this.model.makeRecord(fieldInfo.modelName, [{
                fields: [{
                    name: 'id',
                    type: 'integer',
                }, {
                    name: 'display_name',
                    type: 'char',
                }],
                name: fieldName,
                relation: fieldInfo.modelName,
                type: 'many2many',
                value: fieldInfo.value,
            }], options).then(function (recordID) {
                self.widgets[fieldName] = new RelationalFields.FieldMany2ManyTags(self,
                    fieldName,
                    self.model.get(recordID),
                    { mode: 'edit', }
                );
                self._registerWidget(recordID, fieldName, self.widgets[fieldName]);
            });
        },
    });

    accountReportsWidget.include({
        custom_events: _.extend({}, accountReportsWidget.prototype.custom_events, {
            'range_account_filter_changed': function (ev) {
                var self = this;
                self.report_options.account_accounts = ev.data.account_accounts;
                self.report_options.account_accounts_to = ev.data.account_accounts_to;
                return self.reload().then(function () {
                    self.$searchview_buttons.find('.account_accounts_filter').click();
                });
            },
        }),
        init: function (parent, action) {
            return this._super.apply(this, arguments);
        },
        render_searchview_buttons: function () {
            this._super.apply(this, arguments);

            // filter range account
            console.log('options: ' + this)
            if (this.report_options.range_account) {

                console.log(this.report_options.range_account)
                if (!this.range_account_m2m_filter) {
                    var fields = {};
                    if (this.report_options.account_accounts) {
                        fields['account_accounts'] = {
                            label: _t('Accounts From'),
                            modelName: 'account.account',
                            value: this.report_options.account_accounts
                        };
                    }
                    if (this.report_options.account_accounts_to) {
                        fields['account_accounts_to'] = {
                            label: _t('Accounts To'),
                            modelName: 'account.account',
                            value: this.report_options.account_accounts_to
                        };
                    }
                    if (!_.isEmpty(fields)) {
                        this.range_account_m2m_filter = new M2MFilters(this, fields, 'range_account_filter_changed');
                        this.range_account_m2m_filter.appendTo(this.$searchview_buttons.find('.js_account_accounts_m2m'));
                    }
                } else {
                    this.$searchview_buttons.find('.js_account_accounts_m2m').append(this.range_account_m2m_filter.$el);
                }
            }

        },

    });
});
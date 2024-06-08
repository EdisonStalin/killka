odoo.define('oe_account.account_payment', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var field_utils = require('web.field_utils');

var QWeb = core.qweb;
var _t = core._t;

var ShowPaymentLineWidgetInherit = AbstractField.extend({
	
	events: _.extend({
        'click .outstanding_credit_assign': '_onOutstandingCreditAssign',
    }, AbstractField.prototype.events),
    supportedFieldTypes: ['char'],

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {boolean}
     */
    isSet: function() {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _render: function() {
        var self = this;
        var info = JSON.parse(this.value);
        if (!info) {
            this.$el.html('');
            return;
        }
        _.each(info.content, function (k, v){
            k.index = v;
            k.amount = field_utils.format.float(k.amount, {digits: k.digits});
            if (k.date){
                k.date = field_utils.format.date(field_utils.parse.date(k.date, {}, {isUTC: true}));
            }
        });
        this.$el.html(QWeb.render('ShowPaymentInfo', {
            lines: info.content,
            outstanding: info.outstanding,
            title: info.title
        }));
        _.each(this.$('.js_payment_info'), function (k, v){
            var content = info.content[v];
            var options = {
                content: function () {
                    var $content = $(QWeb.render('PaymentPopOver', {
						title: content.title,
                        name: content.name,
                        journal_name: content.journal_name,
                        date: content.date,
                        amount: content.amount,
                        currency: content.currency,
                        position: content.position,
                        payment_id: content.payment_id,
                        move_id: content.move_id,
                        ref: content.ref,
                        account_payment_id: content.account_payment_id,
                        invoice_id: content.invoice_id,
                        withholding_id: content.withholding_id,
                        cross: content.cross,
                    }));
                    $content.filter('.js_unreconcile_payment').on('click', self._onRemoveMoveReconcile.bind(self));
                    $content.filter('.js_open_payment').on('click', self._onOpenPayment.bind(self));
                    return $content;
                },
                html: true,
                placement: 'left',
                title: _t('Transaction Information'),
                trigger: 'focus',
                delay: { "show": 0, "hide": 200 },
            };
            $(k).popover(options);
        });
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    _onOpenPayment: function (event) {
        var invoiceId = parseInt($(event.target).attr('invoice-id'));
        var paymentId = parseInt($(event.target).attr('payment-id'));
        var withholdingId = parseInt($(event.target).attr('withholding-id'));
        var moveId = parseInt($(event.target).attr('move-id'));
        var res_model;
        var id;
        if (invoiceId !== undefined && !isNaN(invoiceId)){
            res_model = "account.invoice";
            id = invoiceId;
        } else if (paymentId !== undefined && !isNaN(paymentId)){
            res_model = "account.payment";
            id = paymentId;
        } else if (withholdingId !== undefined && !isNaN(withholdingId)){
            res_model = "account.withholding";
            id = withholdingId;
        } else if (moveId !== undefined && !isNaN(moveId)){
            res_model = "account.move";
            id = moveId;
        }
        //Open form view of account.move with id = move_id
        if (res_model && id) {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: res_model,
                res_id: id,
                views: [[false, 'form']],
                target: 'current'
            });
        }
    },
    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    _onOutstandingCreditAssign: function (event) {
        var self = this;
        var id = $(event.target).data('id') || false;
        var line_id = JSON.parse(this.value).invoice_id
        if (self.model == 'account.withholding'){
        	line_id = JSON.parse(this.value).withholding_id
        }
        this._rpc({
                model: self.model,
                method: 'assign_outstanding_credit',
                args: [line_id, id],
            }).then(function () {
                self.trigger_up('reload');
            });
    },
    /**
     * @private
     * @override
     * @param {MouseEvent} event
     */
    _onRemoveMoveReconcile: function (event) {
        var self = this;
        var paymentId = parseInt($(event.target).attr('payment-id'));
        var withholdingId = parseInt($(event.target).attr('withholding-id'));
        if (paymentId !== undefined && !isNaN(paymentId)) {
            this._rpc({
                model: 'account.move.line',
                method: 'remove_move_reconcile',
                args: [paymentId, {'invoice_id': this.res_id, 'withholding_id': withholdingId}]
            }).then(function () {
                self.trigger_up('reload');
            });
        }
    },
});

field_registry.add('payment', ShowPaymentLineWidgetInherit);

});
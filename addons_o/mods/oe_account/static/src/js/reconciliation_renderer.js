odoo.define('oe_account.ReconciliationRendererInherit', function (require) {
	"use strict";
	var core = require('web.core');
	var qweb = core.qweb;
	var _t = core._t;

	var lineRenderer = require('account.ReconciliationRenderer').LineRenderer;

	lineRenderer.include({
	//--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * update the statement line rendering
     *
     * @param {object} state - statement line
     */
    update: function (state) {
        var self = this;
        // isValid
        this.$('caption .o_buttons button.o_validate').toggleClass('hidden', !!state.balance.type);
        this.$('caption .o_buttons button.o_reconcile').toggleClass('hidden', state.balance.type <= 0);
        this.$('caption .o_buttons .o_no_valid').toggleClass('hidden', state.balance.type >= 0);

        // partner_id
        this._makePartnerRecord(state.st_line.partner_id, state.st_line.partner_name).then(function (recordID) {
            self.fields.partner_id.reset(self.model.get(recordID));
            self.$el.attr('data-partner', state.st_line.partner_id);
        });

        // mode
        this.$('.create, .match').each(function () {
            var $panel = $(this);
            $panel.css('-webkit-transition', 'none');
            $panel.css('-moz-transition', 'none');
            $panel.css('-o-transition', 'none');
            $panel.css('transition', 'none');
            $panel.css('max-height', $panel.height());
            $panel.css('-webkit-transition', '');
            $panel.css('-moz-transition', '');
            $panel.css('-o-transition', '');
            $panel.css('transition', '');
        });
        this.$el.data('mode', state.mode).attr('data-mode', state.mode);
        this.$('.create, .match').each(function () {
            $(this).removeAttr('style');
        });

        // reconciliation_proposition
        var $props = this.$('.accounting_view tbody').empty();

        // loop state propositions
        var props = [];
        var partialDebitProps = 0;
        var partialCreditProps = 0;
        _.each(state.reconciliation_proposition, function (prop) {
            if (prop.display) {
                props.push(prop);
                if (prop.amount > 0 && prop.amount > state.st_line.amount) {
                    partialDebitProps++;
                } else if (prop.amount < 0 && prop.amount < state.st_line.amount) {
                    partialCreditProps++;
                }

            }
        });

        var targetLineAmount = state.st_line.amount;
        _.each(props, function (line) {
            var $line = $(qweb.render("reconciliation.line.mv_line", {'line': line, 'state': state}));
            if (!isNaN(line.id)) {
                $('<span class="line_info_button fa fa-info-circle"/>')
                    .appendTo($line.find('.cell_info_popover'))
                    .attr("data-content", qweb.render('reconciliation.line.mv_line.details', {'line': line}));
            }
            if (line.already_paid === false &&
                ((state.balance.amount_currency < 0 || line.partial_reconcile)
                    && line.amount > 0 && state.st_line.amount > 0 && targetLineAmount < line.amount && partialDebitProps <= 1) ||
                ((state.balance.amount_currency > 0 || line.partial_reconcile)
                    && line.amount < 0 && state.st_line.amount < 0 && targetLineAmount > line.amount && partialCreditProps <= 1)) {
                var $cell = $line.find(line.amount > 0 ? '.cell_right' : '.cell_left');
                var text;
                if (line.partial_reconcile) {
                    text = _t("Undo the partial reconciliation.");
                    $cell.text(line.write_off_amount_str);
                } else {
                    text = _t("This move's amount is higher than the transaction's amount. Click to register a partial payment and keep the payment balance open.");
                }

                $('<span class="do_partial_reconcile_'+(!line.partial_reconcile)+' line_info_button fa fa-exclamation-triangle"/>')
                    .prependTo($cell)
                    .attr("data-content", text);
            }
            targetLineAmount -= line.amount;

            $props.append($line);
        });
	
        // mv_lines
        var $mv_lines = this.$('.match table tbody').empty();
        var stateMvLines = state.mv_lines || [];
		var list_type = ["payable","receivable"];
        _.each(stateMvLines.slice(0, state.limitMoveLines), function (line) {
			
        	if (state.st_line.journal_id === line.journal_id[0] &&  list_type.includes(line.account_type) === false){
	        	var $line = $(qweb.render("reconciliation.line.mv_line", {'line': line, 'state': state}));
	            if (!isNaN(line.id)) {
	                $('<span class="line_info_button fa fa-info-circle"/>')
	                    .appendTo($line.find('.cell_info_popover'))
	                    .attr("data-content", qweb.render('reconciliation.line.mv_line.details', {'line': line}));
	            }
	            $mv_lines.append($line);
        	}
        });
        this.$('.match .fa-chevron-right').toggleClass('disabled', stateMvLines.length <= state.limitMoveLines);
        this.$('.match .fa-chevron-left').toggleClass('disabled', !state.offset);
        this.$('.match').css('max-height', !stateMvLines.length && !state.filter.length ? '0px' : '');

        // balance
        this.$('.popover').remove();
        this.$('table tfoot').html(qweb.render("reconciliation.line.balance", {'state': state}));

        // filter
        if (_.str.strip(this.$('input.filter').val()) !== state.filter) {
            this.$('input.filter').val(state.filter);
        }

        // create form
        if (state.createForm) {
            if (!this.fields.account_id) {
                this._renderCreate(state);
            }
            var data = this.model.get(this.handleCreateRecord).data;
            this.model.notifyChanges(this.handleCreateRecord, state.createForm).then(function () {
                var record = self.model.get(self.handleCreateRecord);
                _.each(self.fields, function (field, fieldName) {
                    if (self._avoidFieldUpdate[fieldName]) return;
                    if (fieldName === "partner_id") return;
                    if ((data[fieldName] || state.createForm[fieldName]) && !_.isEqual(state.createForm[fieldName], data[fieldName])) {
                        field.reset(record);
                    }
                });
            });
        }
        this.$('.create .add_line').toggle(!!state.balance.amount_currency);
    }
		
	});
});
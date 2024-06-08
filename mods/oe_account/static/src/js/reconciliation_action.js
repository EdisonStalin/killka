odoo.define('oe_account.ReconciliationClientActionInherit', function (require) {
	"use strict";
	
	var statementAction = require('account.ReconciliationClientAction').StatementAction;
	
	statementAction.include({
	    /**
	     * @override
	     * @param {Object} params
	     * @param {Object} params.context
	     *
	     */
	    init: function (parent, params) {
			this.config.defaultDisplayQty = 50;
			this.config.limitMoveLines = 15;
	    	this._super.apply(this, arguments);
	    },

	});
});
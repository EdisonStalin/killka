odoo.define('oe_web.form_edit', function(require) {
"use strict";

var FormController = require('web.FormController');

FormController.include({
	_onBounceEdit: function () {
		if (this.$buttons) {
			this._setMode('edit');
		}
	},

})
return FormController;
});
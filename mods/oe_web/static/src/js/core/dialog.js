odoo.define('oe_web.Dialog', function (require) {
"use strict";

	var Dialog = require('web.Dialog');

    Dialog.include({
        open: function() {
            var self = this;
            this._super.apply(this, arguments);
            this.set('title_part', {"zopenerp": document.title});
        },
    });
    
});
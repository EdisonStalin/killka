odoo.define('oe_pos_restaurant.multiprint', function (require) {
"use strict";

    // DIFFERENCES FROM ORIGINAL: 
    // * Printer class is copy-pasted, but added to returns to be extendable
    // * PosModel::initialize is updated to use this Printer class
    var models = require('point_of_sale.models');
    var pos = models.PosModel;
	var Printer = require("pos_restaurant.base");

	pos.prototype.models.forEach(function(m) {
		if (m.model == 'restaurant.printer')
			m.fields.push('physical_printer');
	});

    Printer.include({
        print: function(receipt) {
            var self = this;
            if (this.config.physical_printer) {
                if (receipt) {
                    this.receipt_queue.push(receipt);
                }
                var send_printing_job = function() {
                    if (self.receipt_queue.length > 0) {
                        var r = self.receipt_queue.shift();
		                var a = window.open('', '', 'height=500, width=500');
		                a.document.write(r);
		                a.document.close();
		                a.focus();
		                a.print();
		                a.close();
                    }
                };
                send_printing_job();
            } else {
                this._super(receipt);
            }
        },
    });

    //return Printer;

});
// quita "Odoo" en diferentes lugares
odoo.define('oe_web.title', function (require) {
	"use strict";	
	var WebClient = require('web.WebClient');

	// quita imagen "Odoo"
	WebClient.include({
		init: function() {
        	this._super.apply(this, arguments);
        	this.set('title_part', {"zopenerp": document.title});
    	},
	});

});

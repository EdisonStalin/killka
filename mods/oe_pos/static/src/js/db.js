odoo.define('oe_pos.DB', function (require) {
"use strict";

var db = require('point_of_sale.DB');

//Search for Fistname, lastname, vat, email
db.include({
	add_barcodes: function(barcodes){
		for(var i = 0, len = barcodes.length; i < len; i++){
			var barcode = barcodes[i];
			this.product_by_barcode[barcode.name] = this.product_by_id[barcode.product_id[0]];
		}
	},
	_partner_search_string: function(partner) {
        var str =  partner.name;
        if(partner.vat){
            str += '|' + partner.vat;
        }
        if(partner.name){
            str += '|' + partner.name;
        }
        if(partner.firstname){
            str += '|' + partner.firstname;
        }
        if(partner.lastname){
            str += '|' + partner.lastname;
        }
        if(partner.phone){
            str += '|' + partner.phone.split(' ').join('');
        }
        if(partner.mobile){
            str += '|' + partner.mobile.split(' ').join('');
        }
        if(partner.email){
            str += '|' + partner.email;
        }
        str = '' + partner.id + ':' + str.replace(':','') + '\n';
        return str;
	},
});

});
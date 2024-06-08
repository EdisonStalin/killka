odoo.define('oe_account_import.import', function (require) {
	"use strict";

	var session = require('web.session');
	
	var baseImport = require('base_import.import').DataImport;
	
	baseImport.include({
	    create_model: function() {
	    	var arg = {res_model: this.res_model};
	    	var context = this.parent_context;
	    	if ('type' in context){
	    		arg['type_document'] = context['type'];
	    	}
	        return this._rpc({
	                model: 'base_import.import',
	                method: 'create',
	                args: [arg],
	                kwargs: {context: session.user_context},
	            });
	    },		
	});
	
});
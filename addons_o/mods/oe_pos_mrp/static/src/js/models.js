odoo.define('oe_pos_mrp_order.models_mrp_order', function (require) {
"use strict";

var pos_model = require('point_of_sale.models');
var pos_screens = require('point_of_sale.screens');
var models = pos_model.PosModel.prototype.models;
var rpc = require('web.rpc');
var core = require('web.core');
var _t = core._t;

for(var i=0; i<models.length; i++){
    var model=models[i];
    if(model.model === 'product.product'){
        model.fields.push('to_make_mrp');
    }
}

pos_screens.PaymentScreenWidget.include({
	validate_order: function(force_validation) {
		var self = this
		this._super(force_validation);
		var order = self.pos.get_order();
		var order_line = order.orderlines.models;
		for (var i in order_line)
		{
			var list_product = []
			if (order_line[i].product.to_make_mrp)
			{
				if (order_line[i].quantity>0)
				{
					var product_dict = {
				        'id': order_line[i].product.id,
						'qty': order_line[i].quantity,
						'product_tmpl_id': order_line[i].product.product_tmpl_id[0],
						'pos_reference': order.name,
						'uom_id': order_line[i].product.uom_id[0],
					};
					list_product.push(product_dict);
				}
			}
			if (list_product.length)
			{
			    try {
					rpc.query({
				        model: 'mrp.production',
				        method: 'create_mrp_from_pos',
				        args: [1, list_product],}
				    ).then(function (result) {
	                	console.log(_t('Generation MRP to order:') + result);
	                }).fail(function (error) {
		            	self.gui.show_popup('alert',{
		                    'title': _t('Error: Process is stopped'),
		                    'body': _.str.sprintf(_t('Tell the administrator that you are having problems in the current process,\n you can continue with the sale, accept the indication and inform the administrator: %s'), error),
		                });
		            	return false;
	                });
	            }catch(err){
	            	self.gui.show_popup('alert',{
	                    'title': _t('Error: Process is stopped'),
	                    'body': _.str.sprintf(_t('Tell the administrator that you are having problems in the current process,\n you can continue with the sale, accept the indication and inform the administrator: %s'), err),
	                });
	            	return false;
	            }
			}
		}
	},

});

});

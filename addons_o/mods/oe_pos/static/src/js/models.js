odoo.define('oe_pos.models', function(require) {
    "use strict";

    var models = require('point_of_sale.models');
    var pos = models.PosModel;
    var core = require('web.core');
	var utils = require('web.utils');
	var round_pr = utils.round_precision;
    var _t = core._t;
    
    // Campos que se descargan de la base
    
    models.load_models({
        model:  'res.country.state',
        fields: ['name', 'code'],
        domain: function(self) {return [['country_id', '=', self.company && self.company.country_id[0] || false]]},
        loaded: function(self,states){
            self.states = states;
            self.company.state = null;
            for (var i = 0; i < states.length; i++) {
                if (states[i].id === self.company.state_id[0]){
                    self.company.state = states[i];
                }
            }
        },
    });
    
	models.load_models({
        model:  'l10n_latam.identification.type',
        fields: [],
        domain: [['is_vat','=',true]],
        loaded: function(self, identifications){
            self.identifications = identifications;
        }
    });

	models.load_models({
        model:  'product.barcode.multi',
        fields: [],
        domain: [],
        loaded: function(self, barcodes){
            self.barcodes = barcodes;
            self.db.add_barcodes(barcodes);
        }
    });

    function checkCustomerFinal(partner){
		return partner.vat == '9999999999999'
	}
    
	pos.prototype.models.forEach(function(m) {
		if (m.model == 'res.company')
			m.fields.push('state_id');
		if (m.model == 'res.partner')
		{
			m.fields.push('firstname', 'lastname', 'limit_amount','type_vat','company_type','l10n_latam_identification_type_id');
			m.loaded = function(self, partners) {
	            const result = partners.filter(checkCustomerFinal)
	            if (result.length === 0)
	            {
	            	console.log(_t('End consumer NOT found or misconfigured.'))
	            }
	            else {
					partners = [result[0]].concat(partners)
				}
	            self.partners = partners;
	            self.db.add_partners(partners);
			}
		}
		if (m.model == 'product.product')
			m.fields.push('barcode_ids');
		if (m.model == 'pos.category')
			m.fields.push('not_view_pos');
		if (m.model == 'decimal.precision')
		{
			m.fields.push('display_digits');
			m.loaded = function(self, dps) {
				self.dp  = {};
				self.dp_show  = {};
	            for (var i = 0; i < dps.length; i++) {
	            	self.dp[dps[i].name] = dps[i].digits;
	            	self.dp_show[dps[i].name] = dps[i].display_digits;
	            }
			}
		}
	});
	
    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function() {
            _super_order.initialize.apply(this, arguments);
            if (this.pos.config.default_partner_id) {
            	this.set_client(this.pos.db.get_partner_by_id(this.pos.config.default_partner_id[0]));
            }
            /*this.to_invoice = true;*/
        },
        init_from_JSON: function (json) {
        	_super_order.init_from_JSON.apply(this, arguments);            
        	if (json.to_invoice) {
                this.to_invoice = json.to_invoice;
            }
        	this.return_ref = json.return_ref;
        },
        export_as_JSON: function(){
            var json = _super_order.export_as_JSON.apply(this,arguments);
            json.return_ref = this.return_ref;
            return json;
        },
        add_product: function (product, options) {
            var order = this.pos.get_order();
            _super_order.add_product.call(this, product, options);
            if (options !== undefined) {
                if (options.extras !== undefined) {
                    for (var prop in options.extras) {
                        if (prop === 'return_ref') {
                            this.return_ref = options.extras['return_ref']
                            this.trigger('change', this);
                        }
                        if (prop === 'label') {
                            order.selected_orderline.set_line_id(options.extras['label']);
                        }
                    }
                }
            }

        },
		get_base_0_taxes: function() {
			return round_pr(this.orderlines.reduce((function(sum, orderLine) {
	            var all_prices = orderLine.get_all_prices();
				if (all_prices.tax == 0.00) {
					sum = sum + all_prices.priceWithoutTax;	
				}
				return sum;
	        }), 0), this.pos.currency.rounding);			
		},
		get_base_taxes: function() {
			return round_pr(this.orderlines.reduce((function(sum, orderLine) {
	            var all_prices = orderLine.get_all_prices();
				if (all_prices.tax >= 0.01) {
					sum = sum + all_prices.priceWithoutTax;	
				}
				return sum;
	        }), 0), this.pos.currency.rounding);			
		},
    });
	
    var _super_pos_model = models.PosModel.prototype;
    
    models.PosModel = models.PosModel.extend({
        get_product_image_url: function (product) {
            return window.location.origin + '/web/image?model=product.product&field=image_medium&id=' + product.id;
        },
    });

    var _super_order_line = models.Orderline.prototype;
    
    models.Orderline = models.Orderline.extend({
        get_display_unit: function(){
        	return this.get_unit_price();
        }
    });
    
	var push_and_invoice_order = pos.prototype.push_and_invoice_order;
	pos.prototype.push_and_invoice_order = function(order){
        var self = this;
        var invoiced = new $.Deferred();
        
        if(!order.get_client()){
            invoiced.reject({code:400, message:'Missing Customer', data:{}});
            return invoiced;
        }

        var order_id = this.db.add_order(order.export_as_JSON());

        this.flush_mutex.exec(function(){
            var done = new $.Deferred(); // holds the mutex

            // send the order to the server
            // we have a 2 seconds timeout on this push.
            // FIXME: if the server takes more than 2 seconds to accept the order,
            // the client will believe it wasn't successfully sent, and very bad
            // things will happen as a duplicate will be sent next time
            // so we must make sure the server detects and ignores duplicated orders

            var transfer = self._flush_orders([self.db.get_order(order_id)], {timeout:15000, to_invoice:true});

            transfer.fail(function(error){
                invoiced.reject(error);
                done.reject();
            });

            // on success, get the order id generated by the server
            transfer.pipe(function(order_server_id){

                // generate the pdf and download it
                if (order_server_id.length) {
                	console.log(_t('Sent Invoice to SRI'));
                    invoiced.resolve();
                    done.reject();
                } else {
                    // The order has been pushed separately in batch when
                    // the connection came back.
                    // The user has to go to the backend to print the invoice
                    invoiced.reject({code:401, message:'Backend Invoice', data:{order: order}});
                    done.reject();
                }
            });

            return done;

        });

        return invoiced;
    };
    
});
odoo.define('oe_pos.pos_service', function(require) {
"use strict";

var screens = require('point_of_sale.screens');
var popups = require('point_of_sale.popups');
var gui = require('point_of_sale.gui');

var PosServiceWidget = screens.ActionButtonWidget.extend({
    template: 'PosServiceWidget',
    renderElement: function(){
	    var self = this;
	    this._super();
	    
      	this.$el.click(function(){
      		var selectedOrder = self.pos.get_order();
      		var category = self.pos.config.service_category_id;
      		var categ = self.pos.db.get_product_by_category(category[0])
      		
            var products = self.pos.db.get_product_by_category(category[0])[0];
	        if (self.pos.db.get_product_by_category(self.pos.config.service_category_id[0]).length == 1) { 
	            selectedOrder.add_product(products);
	        	self.pos.set_order(selectedOrder);
	        	self.gui.show_screen('products');
            }
	        else{
            	var orderlines = self.pos.db.get_product_by_category(category[0]);
                for(var i = 0 ; i<orderlines.length ; i++){
                     orderlines[i]['image_url'] = window.location.origin + '/web/binary/image?model=product.product&field=image_medium&id=' + orderlines[i].id;
                }
            	self.gui.show_popup('pos_service_popup_widget', {'orderlines': orderlines});
            }
        });
	},
	button_click: function(){},
		highlight: function(highlight){
		this.$el.toggleClass('highlight',!!highlight);
	},

});

screens.define_action_button({
    'name': 'Pos Service Widget',
    'widget': PosServiceWidget,
    'condition': function() {
        return true;
    },
});


// PosservicePopupWidget Popup start

var PosServicePopupWidget = popups.extend({
    template: 'PosServicePopupWidget',
    init: function(parent, args) {
        this._super(parent, args);
        this.options = {};
    },
    events: {
        'click .product.service-category': 'click_on_service_product',
        'click .button.cancel': 'click_cancel',
    },
    
    click_on_service_product: function(event) {
        var self = this;
        var service_id = parseInt(event.currentTarget.dataset['productId'])
        self.pos.get_order().add_product(self.pos.db.product_by_id[service_id]);
        self.pos.gui.close_popup();
    },
});
gui.define_popup({name: 'pos_service_popup_widget', widget: PosServicePopupWidget});

});
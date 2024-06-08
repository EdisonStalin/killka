odoo.define('pos_combo_pack.pos_product_pack_file', function (require) {
"use strict";
    var screens = require('point_of_sale.screens');
    var models = require('point_of_sale.models');
    var PopUpWidget=require('point_of_sale.popups');
    var gui = require('point_of_sale.gui');
    var _t  = require('web.core')._t;
    var Model = this;
    var core = require('web.core');
    var QWeb = core.qweb;
    var utils = require('web.utils');
    var round_di = utils.round_decimals;


    models.load_fields("product.product",['product_pack_id', 'product_fix_pro_ids','is_pack','is_extra', 'product_extra_id']);

    models.load_models({
        model: 'product.pack',
        fields: ['id','product_categ_id','product_quantity','is_extra','default_product_id'],
        loaded: function(self,result){
            self.set({'pack_product': result});
        },
      
    });
    models.load_models({
        model: 'fix.product.pack',
        fields: ['id','product_p_id','product_quantity'],
        loaded: function(self,result){
            self.set({'fix_pack_product': result});
        },
      
    });
    models.load_models({
        model: 'product.extra.topping',
        fields: ['id','product_categ_id','multi_selection'],
        loaded: function(self,result){
            self.set({'extra_product_topping': result});
        },
    });

    var OwnPizzaWidget = PopUpWidget.extend({
        template : 'OwnPizzaWidget',
        show : function(options) {
            var self = this;
            this._super();
            this.data = options.data
            this.main_product = options.main_product
            this.renderElement();
            this.order_menu = [];
            var order_menu = [];
            $(".pos_topp_product").click(function(){
                var product_id = $(this).data('product-id');
                var category_id = $(this).data('category-id');
                var multi_selection = $(this).data('multi_selection');
                var category = self.pos.db.get_category_by_id(category_id);
                var product = self.pos.db.get_product_by_id(product_id);
                var allow = true;
                for(var i=0;i<order_menu.length;i++){
                    if(category_id == order_menu[i].categoryId){
                        var allow2 = true;
                        for(var j=0;j<order_menu[i].products.length;j++){
                            if(order_menu[i].products[j].product_id == product_id){
                                order_menu[i].products.splice(j, 1)
                                allow2 = false;
                                $(this).removeClass("green_border");
                            }
                        }
                        if(order_menu[i].products.length > 0 && multi_selection == false){
                            alert("You can select only one item.");
                        }else{
                            if(allow2){
                                order_menu[i].products.push({'product_id':product_id,'product_name':product.display_name,'price':product.list_price});
                                $(this).addClass("green_border");
                            }  
                        }
                        allow = false;
                    }
                    if(order_menu[i].products.length <= 0){
                        order_menu.splice(i, 1)
                    }
                }
                if(allow){
                    $(this).addClass("green_border");
                    order_menu.push({'categoryId':category_id,'categoryName':category.name,'products':[{'product_id':product_id,'product_name':product.display_name,'price':product.list_price}]});
                }
                self.display_order_line(order_menu);
                self.order_menu = order_menu;
            });
        },
        display_order_line:function(order_menu){
            var html_text = "<table width='100%'>"
            var total_price = 0;
            for(var i=0;i<order_menu.length;i++){
                html_text += "<tr><td style='float:left'><b style='font-size: 11px;color: black'>"+order_menu[i].categoryName+"</td></b><td></td></tr>";
                for(var j=0;j<order_menu[i].products.length;j++){
                    html_text += "<tr><td style='float:left;margin-left: 10px;'>"+order_menu[i].products[j].product_name+"</td><td style='float:right;margin-right: 10px;'>"+(order_menu[i].products[j].price).toFixed(2)+"</td></tr>";
                    total_price += order_menu[i].products[j].price;
                }
            }
            html_text += "</table>"
            $(".order-menu").html(html_text);
            $(".total-pricel").html(total_price.toFixed(2));
        },
        click_confirm: function(){
            var self = this;
            var own_data = [];
            var selection = [];
            var order_menu = this.order_menu;
            var total_price = 0;        
            for(var i=0;i<order_menu.length;i++){
                for(var j=0;j<order_menu[i].products.length;j++){
                    var product_id = order_menu[i].products[j].product_id
                    own_data.push({"product_id":self.pos.db.get_product_by_id(parseInt(product_id)), 'qty':1,'price':self.pos.db.get_product_by_id(parseInt(product_id)).list_price});
                    total_price += self.pos.db.get_product_by_id(product_id).list_price;
                }
            }
            var order = this.pos.get('selectedOrder');
            var product = this.pos.db.get_product_by_id(parseInt($(".main_product_id").data('product_id')));
            order.add_product(product,{'price':total_price, 'merge':false});
            order.selected_orderline.own_data = own_data;
            order.selected_orderline.order_menu = order_menu;
            order.selected_orderline.set_selected();
            this.gui.close_popup();
        },
    });

    gui.define_popup({name:'ownpizza', widget: OwnPizzaWidget});

    screens.ProductScreenWidget.include({
        click_product: function(product) {
            var self = this
            if(product.to_weight && this.pos.config.iface_electronic_scale){
                this.gui.show_screen('scale',{product: product});
            }else{
                var order = self.pos.get_order()
                if(product.is_extra){
                    var data = [];
                    _.each(self.pos.get('extra_product_topping'), function(extra){
                        if( product.product_extra_id.indexOf(extra.id) >=0){
                            data.push({
                            	'category':extra.product_categ_id[1], 
                            	'categ_id':extra.product_categ_id[0],
                            	'multi_selection':extra.multi_selection,
                                'products':self.pos.db.get_product_by_category(extra.product_categ_id[0]),
                                'qty':extra.product_quantity})
                        }
                    });
                    self.gui.show_popup('ownpizza',{
                        'data':data, 
                        'main_product':product.id
                    });
                }
                else if(product.is_pack){
                    var data = [];
                    var fix_pack_data = [];
                    _.each(self.pos.get('pack_product'), function(pack){
                        if( product.product_pack_id.indexOf(pack.id) >=0){
                            data.push({
                            	'category':pack.product_categ_id[1],
                            	'categ_id':pack.product_categ_id[0],
                                'products':self.pos.db.get_product_by_category(pack.product_categ_id[0]), 
                                'qty':pack.product_quantity,
                                'is_extra':pack.is_extra,
                                'default':pack.default_product_id})
                        }
                    });
                    _.each(self.pos.get('fix_pack_product'), function(pack){
                        if( product.product_fix_pro_ids.indexOf(pack.id) >=0){
                            fix_pack_data.push({'product':self.pos.db.get_product_by_id(pack.product_p_id[0]), 'qty':pack.product_quantity})
                        }
                    });
                    self.gui.show_popup('combopack',{
                        'fix_pack_data':fix_pack_data,
                        'data':data, 
                        'main_product':product.id
                    });
                }
                else{
                    this.pos.get_order().add_product(product);
                } 
            }
        }
    });

    
    var _super_order_line = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        init_from_JSON: function(json) {
        	_super_order_line.init_from_JSON.apply(this,arguments);
        	var self = this
        	if(json.is_pack){
        		this.pack_data = []
        		_.each(json.combo_ids, function(item){
        			item = item[2]
        			self.pack_data.push({'product_id':item.name,'qty':item.qty * json.qty});
                })
        	}
        	if(json.is_extra){
        		this.order_menu = json.order_menu
        	}
        },
        export_as_JSON: function(){
            var self = this;
            var own_line = [];
            var total_price = 0;
            var json = _super_order_line.export_as_JSON.call(this,arguments);
            if(this.product.is_extra && this.own_data){
                _.each(this.own_data, function(item){
                    own_line.push([0, 0, {'product_id':item.product_id.id,'name':item.product_id, 'qty':self.get_quantity(),'price':item.price}]);
                    total_price += item.price;
                });
                json.order_menu = this.order_menu
            }
            if (this.product.is_extra){
                json.price_unit = total_price;
                this.price = total_price;
            }
            else {
            	json.price_unit = this.price;
            }
            json.is_extra = this.product.is_extra;
            json.own_ids = this.product.is_extra ? own_line : [];
            var combo_line = []
            if(self.product.is_pack && self.pack_data){
                _.each(self.pack_data, function(item){
                    combo_line.push([0, 0, {'product_id':item.product_id.id,'name':item.product_id, 'qty':item.qty * self.get_quantity()}]);
                })
            }
            json.is_pack = this.product.is_pack;
            json.combo_ids = this.product.is_pack ? combo_line : [];
            return json;
        },
    });


    var ComboPackWidget = PopUpWidget.extend({
    	template : 'ComboPack',
    	show : function(options) {
    		var self = this;
    		this._super();
    		this.data = options.data;
            this.fix_pack_data = options.fix_pack_data;
    		this.main_product = options.main_product;
    		this.renderElement();
    	},
    	click_confirm: function(){
    		var pack_data = [];
    		var product_data = [];
    		var self = this;
    		var product = this.pos.db.get_product_by_id(parseInt($(".combo_product_id").data('product_id')));
    		_.each($(".product_combo_select"),function(p_s){
    			if($(p_s).val() != "Select Your Food...."){
    				var product_id = self.pos.db.get_product_by_id(parseInt($(p_s).val()));
    				if ($(p_s).data('is_extra')===false){
    					pack_data.push({"product_id": product_id, 'qty':$(p_s).data('qty')})
    				} else {
    					product_data.push(product_id);
    				}
    					
    			}
    		});
            _.each(self.pos.get('fix_pack_product'), function(pack){
                if( product.product_fix_pro_ids.indexOf(pack.id) >=0){
                    pack_data.push({"product_id":self.pos.db.get_product_by_id(pack.product_p_id[0]), 'qty':pack.product_quantity})
                }
            });

            var order = this.pos.get('selectedOrder');
    		order.add_product(product,{ 'merge':false});
            order.selected_orderline.pack_data = pack_data;
    		_.each(product_data, function(product){
    			order.add_product(product, {'merge':true});
    		});
            order.selected_orderline.set_selected();
            this.gui.close_popup();
        },
    });
    gui.define_popup({name:'combopack', widget: ComboPackWidget});


   
});

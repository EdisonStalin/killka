odoo.define('oe_pos.screens', function (require) {
"use strict";

var screens = require('point_of_sale.screens');
var PopupWidget = require('point_of_sale.popups');
var gui = require('point_of_sale.gui');
var core = require('web.core');
var rpc = require('web.rpc');
var QWeb = core.qweb;
var _t = core._t;
var task;

/*--------------------------------------*\
|         THE RECEIPT SCREEN           |
\*======================================*/

//The receipt screen displays the order's
//receipt and allows it to be printed in a web browser.
//The receipt screen is not shown if the point of sale
//is set up to print with the proxy. Altough it could
//be useful to do so...

screens.ReceiptScreenWidget.include({
    get_receipt_render_env: function() {
    	var order = this.pos.get_order();
    	var value_order = {
            widget: this,
            a2 : window.location.origin + '/web/image?model=pos.config&field=image&id='+this.pos.config.id,
            pos: this.pos,
            order: order,
            receipt: order.export_for_printing(),
            orderlines: order.get_orderlines(),
            paymentlines: order.get_paymentlines(),
        };
        return value_order;
    },
});

/*--------------------------------------*\
|         THE CLIENT LIST              |
\*======================================*/

//The clientlist displays the list of customer,
//and allows the cashier to create, edit and assign
//customers.

screens.ClientListScreenWidget.include({
    show: function(){
        var self = this;
        this._super();
        
        this.$('.new-customer').click(function(){
            self.display_client_details('edit',{
                'country_id': self.pos.company.country_id,
                'state_id': self.pos.company.state_id,
            });
        });
        
    },
	
	// what happens when we save the changes on the client edit form -> we fetch the fields, sanitize them,
    // send them to the backend for update, and call saved_client_details() when the server tells us the
    // save was successfull.
    save_client_details: function(partner) {
        var self = this;
        
        var fields = {};
        this.$('.client-details-contents .detail').each(function(idx,el){
            fields[el.name] = el.value || false;
        });

        if (!fields.firstname) {
            this.gui.show_popup('error',_t('A Customer Name Is Required'));
            return;
        }
        
        if (!fields.vat) {
            this.gui.show_popup('error',_t('A Customer VAT Is Required'));
            return;
        }
        else {
        	var result = validar_doc(fields.vat);
        	if (!result) {
        		self.gui.show_popup('error',_t('Invalid Vat/RUC number, correct Vat/RUC number.'));
        		return;
        	}
        }
        
        if (!fields.email) {
            this.gui.show_popup('error',_t('A Customer Email Is Required'));
            return;
        }
        
        if (!fields.street) {
            this.gui.show_popup('error',_t('A Customer Street Is Required'));
            return;
        }
        
        if (!fields.city) {
            this.gui.show_popup('error',_t('A Customer City Is Required'));
            return;
        }
        
        if (this.uploaded_picture) {
            fields.image = this.uploaded_picture;
        }

        fields.id           = partner.id || false;
        fields.country_id   = fields.country_id || false;

        if (fields.property_product_pricelist) {
            fields.property_product_pricelist = parseInt(fields.property_product_pricelist, 10);
        } else {
            fields.property_product_pricelist = false;
        }
        var contents = this.$(".client-details-contents");
        contents.off("click", ".button.save");


        rpc.query({
                model: 'res.partner',
                method: 'create_from_ui',
                args: [fields],
            })
            .then(function(partner_id){
                self.saved_client_details(partner_id);
            },function(err,ev){
                ev.preventDefault();
                var error_body = _t('Your Internet connection is probably down.');
                if (err.data) {
                    var except = err.data;
                    error_body = except.arguments && except.arguments[0] || except.message || error_body;
                }
                self.gui.show_popup('error',{
                    'title': _t('Error: Could not Save Changes'),
                    'body': error_body,
                });
                contents.on('click','.button.save',function(){ self.save_client_details(partner); });
            });
    },
});

/*--------------------------------------*\
|         THE PRODUCT SCREEN           |
\*======================================*/

/* ------------ The Numpad ------------ */

screens.NumpadWidget.include({
    renderElement: function () {
        this._super();
        $('.numpad-toggle').on('click', function () {
            var self = this;
            $(this).parent().siblings('.numpad-container').slideToggle(function () {
                $(self).toggleClass('fa-caret-down fa-caret-up');
                if($(this).is(':visible')){
                    $('.order-scroller').animate({scrollTop: $('.order-scroller').height()}, 500);
                }
            });
        });
    },
    clickChangeMode: function (event) {
        var self = this;
        var mode = self.state.get('mode');
        var newMode = event.currentTarget.attributes['data-mode'].nodeValue;
        if (mode == newMode) {
            return self.state.changeMode(newMode);
        }
        if (newMode == 'discount') {
            if (self.pos.config.lock_discount == true) {
                self.gui.show_popup('password', {
                    'title': _t('Password?'),
                    confirm: function (pw) {
                        if (pw !== self.pos.config.lock_password) {
                            self.gui.show_popup('error', {
                                'title': _t('Error'),
                                'body': _t('Incorrect password. Please try again'),
                            });
                        } 
                        else {
                            return self.state.changeMode(newMode);
                        }
                    },
                });
            } 
            else {
                return self.state.changeMode(newMode);
            }
        } 
        else if (newMode == 'price') {
            if (self.pos.config.lock_price == true) {
                self.gui.show_popup('password', {
                    'title': _t('Password?'),
                    confirm: function (pw) {
                        if (pw !== self.pos.config.lock_password) {
                            self.gui.show_popup('error', {
                                'title': _t('Error'),
                                'body': _t('Incorrect password. Please try again'),
                            });
                        } else {
                            return self.state.changeMode(newMode);
                        }
                    },
                });
            } else {
                return self.state.changeMode(newMode);
            }
        } else {
            return self.state.changeMode(newMode);
        }
    },
});

/* --------- The Order Widget --------- */

//Displays the current Order.

screens.OrderWidget.include({
    update_summary: function(){
        var order = this.pos.get_order();
        if (!order.get_orderlines().length) {
            return;
        }

        var total = order ? order.get_total_with_tax() : 0;
		var taxes = order ? total - order.get_total_without_tax() : 0;		
		var base_taxes = order ? order.get_base_taxes() : 0;
		var base_0 = order ? order.get_base_0_taxes(): 0;
		var subtotal = order ? order.get_subtotal(): 0;
        
        this.el.querySelector('.summary .total > .value').textContent = this.format_currency(total, 'Account Total', true);
		this.el.querySelector('.summary .total .subtotal .value').textContent = this.format_currency(subtotal, 'Account Total', true);
        this.el.querySelector('.summary .total .base_0 .value').textContent = this.format_currency(base_0, 'Account Total', true);
        this.el.querySelector('.summary .total .base_taxes .value').textContent = this.format_currency(base_taxes, 'Account Total', true);
        this.el.querySelector('.summary .total .subentry .value').textContent = this.format_currency(taxes, 'Account Total', true);
    },
});

/* --------- The Product List --------- */

screens.ProductListWidget.include({
	template: 'ProductListWidget',
    init: function(parent, options) {
        parent.t = this.template;
        var self = this;
        this._super(parent,options);

        this.keypress_product_handler = function(ev){
            // React only to SPACE to avoid interfering with warcode scanner which sends ENTER
            if (ev.which != 13) {
                return;
            }
            ev.preventDefault();
            var product = self.pos.db.get_product_by_id(this.dataset.productId);
            options.click_product_action(product);
        };
    },
    renderElement: function () {
        this._super();
        
        var list_container = this.el.querySelector('.product-list');
        for(var i = 0, len = this.product_list.length; i < len; i++){
            var product_node = this.render_product(this.product_list[i]);
            product_node.addEventListener('keypress',this.keypress_product_handler);
            list_container.appendChild(product_node);
        }
    }
});

/* ------ customizing product screen widget for shortcut ------ */
var ShortcutTipsWidget = PopupWidget.extend({
    template: 'ShortcutTipsWidget',
    show: function () {
        this._super();
    }
});
gui.define_popup({name: 'shortcuttips', widget: ShortcutTipsWidget});

/* ------ The Product Categories ------ */

screens.ProductCategoriesWidget.include({
    renderElement: function(){
        this._super();
        var self = this;
        $(".searchbox input").autocomplete({
            source: function (request, response) {
                response(self.get_product_list(self.category,request.term));
            },
            select: function(event, ui){
                var product = self.pos.db.get_product_by_id(ui.item['id']);
                self.clear_search();
                self.pos.get_order().add_product(product);
                return false;
            },
        });
    },
    get_product_list: function(category,query){
        var product_list = []
        var products;
        if(query){
            products = this.pos.db.search_product_in_category(category.id,query);
        }else{
            products = this.pos.db.get_product_by_category(this.category.id);
        }
        products.map(function(product){
            var values = {
                'id': product.id,
                'values': product.display_name,
            }
            if(product.default_code){
                values['label'] = "["+product.default_code+"] "+product.display_name;
            }else{
                values['label'] = product.display_name;
            }
            product_list.push(values);
        });
        return product_list;
    }
});

/* -------- The Product Screen -------- */

screens.ProductScreenWidget.include({
    init: function(parent, options){
        this._super(parent,options);

        var self = this;

        this.actionpad = new screens.ActionpadWidget(this,{});
        this.actionpad.replace(this.$('.placeholder-ActionpadWidget'));

        this.numpad = new screens.NumpadWidget(this,{});
        this.numpad.replace(this.$('.placeholder-NumpadWidget'));

        this.product_screen_keydown_event_handler = function(event){
        	
        	var enable_popup = false;
        	if (!$($(document).find(".modal-dialog")[7]).hasClass('oe_hidden')){
        		enable_popup = true;
        	}
        	
        	/* product screen key down events */
            if(!$($(document).find(".product-screen")[0]).hasClass('oe_hidden')){
                if(event.which == 113) {      // click on "F2" button
                    $(document).find("div.product-screen div.leftpane span#shortcut_tips_btn").trigger("click");
                }
            }

            if(!$(document).find(".search-input").is(":focus") && 
            		!$($(document).find(".product-screen")[0]).hasClass('oe_hidden') && !enable_popup){
                if(event.which == 81){  // click on "q" button
                    self.numpad.state.changeMode('quantity');
                } else if(event.which == 68){   // click on "d" button
                    self.numpad.state.changeMode('discount');
                } else if(event.which == 80){   // click on "p" button
                    self.numpad.state.changeMode('price');
                } else if(event.which == 8){    // click on "Backspace" button
                    self.numpad.state.deleteLastChar();
                } else if(event.which >= 96 && event.which <= 105) {    // click on numpad 1-9 and 0 button
                    var newChar = String.fromCharCode(event.which - 48 );
                    self.numpad.state.appendNewChar(newChar);
                } else if(event.which == 109) {     // click on numpad "-" button
                    self.numpad.state.switchSign();
                } else if(event.which == 110) {     // click on numpad "." button
                    self.numpad.state.appendNewChar('.');
                } else if(event.which == 67) {      // click on "c" button
                    self.actionpad.gui.show_screen('clientlist');
                } else if(event.which == 32) {      // click on "space" button
                    self.actionpad.gui.show_screen('payment');
                } else if(event.which == 46) {      // click on "Delete" button
                    self.pos.get_order().remove_orderline(self.pos.get_order().get_selected_orderline());
                } else if(event.which == 38) {      // click on "up arrow" button
                    $(document).find("div.product-screen ul.orderlines li.selected").prev('li.orderline').trigger('click');
                } else if(event.which == 40) {      // click on "down arrow" button
                    $(document).find("div.product-screen ul.orderlines li.selected").next('li.orderline').trigger('click');
                } else if(event.which == 115) {      // click on "F4" button
                    $(document).find("div.product-screen div.rightpane div.searchbox input").focus();
                    event.preventDefault();
                }
            }

            /* payment screen key down events */
            if(!$($(document).find("div.payment-screen")[0]).hasClass('oe_hidden')){
                if (event.which == 27) {     // click on "Esc" button
                    $($(document).find("div.payment-screen")[0]).find("div.top-content span.back").trigger('click');
                } else if(event.which == 67) {             // click on "c" button
                    $($(document).find("div.payment-screen")[0]).find("div.js_set_customer").trigger('click');
                } else if (event.which == 73) {     // click on "i" button
                    $($(document).find("div.payment-screen")[0]).find("div.payment-buttons div.js_invoice").trigger('click');
                } else if(event.which == 33) {      // click on "Page Up" button
                    if($($(document).find("div.payment-screen")[0]).find("div.paymentmethods div.highlight").length > 0){
                        var elem = $($(document).find("div.payment-screen")[0]).find("div.paymentmethods div.highlight");
                        elem.removeClass("highlight");
                        elem.prev("div.paymentmethod").addClass("highlight");
                    }else{
                        var payMethodLength = $($(document).find("div.payment-screen")[0]).find("div.paymentmethods div.paymentmethod").length;
                        if(payMethodLength > 0){
                            $($($(document).find("div.payment-screen")[0]).find("div.paymentmethods div.paymentmethod")[payMethodLength-1]).addClass('highlight');
                        }
                    }
                } else if(event.which == 34) {      // click on "Page Down" button
                    if($($(document).find("div.payment-screen")[0]).find("div.paymentmethods div.highlight").length > 0){
                        var elem = $($(document).find("div.payment-screen")[0]).find("div.paymentmethods div.highlight");
                        elem.removeClass("highlight");
                        elem.next("div.paymentmethod").addClass("highlight");
                    }else{
                        var payMethodLength = $($(document).find("div.payment-screen")[0]).find("div.paymentmethods div.paymentmethod").length;
                        if(payMethodLength > 0){
                            $($($(document).find("div.payment-screen")[0]).find("div.paymentmethods div.paymentmethod")[0]).addClass('highlight');
                        }
                    }
                } else if(event.which == 32) {      // click on "space" button
                    event.preventDefault();
                    $($(document).find("div.payment-screen")[0]).find("div.paymentmethods div.highlight").trigger("click");
                    $($(document).find("div.payment-screen")[0]).find("div.paymentmethods div.paymentmethod").removeClass("highlight");
                } else if(event.which == 38) {      // click on "Arrow Up" button
                    if($($(document).find("div.payment-screen")[0]).find("table.paymentlines tbody tr.selected").length > 0){
                        $($(document).find("div.payment-screen")[0]).find("table.paymentlines tbody tr.selected").prev("tr.paymentline").trigger("click");
                    }else{
                        var payLineLength = $($(document).find("div.payment-screen")[0]).find("table.paymentlines tbody tr.paymentline").length;
                        if(payLineLength > 0){
                            $($($(document).find("div.payment-screen")[0]).find("table.paymentlines tbody tr.paymentline")[payLineLength-1]).trigger('click');
                        }
                    }
                } else if(event.which == 40) {      // click on "Arrow Down" button
                    if($($(document).find("div.payment-screen")[0]).find("table.paymentlines tbody tr.selected").length > 0){
                        var elem = $($(document).find("div.payment-screen")[0]).find("table.paymentlines tbody tr.selected").next("tr.paymentline").trigger("click");
                        elem.removeClass("highlight");
                        elem.next("div.paymentmethod").addClass("highlight");
                    }else{
                        var payLineLength = $($(document).find("div.payment-screen")[0]).find("table.paymentlines tbody tr.paymentline").length;
                        if(payLineLength > 0){
                            $($($(document).find("div.payment-screen")[0]).find("table.paymentlines tbody tr.paymentline")[0]).trigger('click');
                        }
                    }
                } else if(event.which == 46) {      // click on "Delete" button
                    event.preventDefault();
                    $($(document).find("div.payment-screen")[0]).find("table.paymentlines tbody tr.selected td.delete-button").trigger("click");
                }
            }

            /* clientlist screen key down events */
            if(!$($(document).find("div.clientlist-screen")[0]).hasClass('oe_hidden')){
                if (event.which == 27) {            // click on "Esc" button
                    $($(document).find("div.clientlist-screen")[0]).find("span.back").trigger('click');
                } else if(event.which == 115) {      // click on "F4" button
                    $(document).find("div.clientlist-screen span.searchbox input").focus();
                    event.preventDefault();
                } else if(event.which == 38) {      // click on "Arrow Up" button
                    if($(document).find("div.clientlist-screen table.client-list tbody.client-list-contents tr.highlight").length > 0){
                        $(document).find("div.clientlist-screen table.client-list tbody.client-list-contents tr.highlight").prev("tr.client-line").click();
                    }else{
                        var clientLineLength = $(document).find("div.clientlist-screen table.client-list tbody.client-list-contents tr.client-line").length;
                        if(clientLineLength > 0){
                            $($(document).find("div.clientlist-screen table.client-list tbody.client-list-contents tr.client-line")[clientLineLength-1]).click();
                        }
                    }
                } else if(event.which == 40) {      // click on "Arrow Down" button
                    if($(document).find("div.clientlist-screen table.client-list tbody.client-list-contents tr.highlight").length > 0){
                        $(document).find("div.clientlist-screen table.client-list tbody.client-list-contents tr.highlight").next("tr.client-line").click();
                    }else{
                        var clientLineLength = $(document).find("div.clientlist-screen table.client-list tbody.client-list-contents tr.client-line").length;
                        if(clientLineLength > 0){
                            $($(document).find("div.clientlist-screen table.client-list tbody.client-list-contents tr.client-line")[0]).click();
                        }
                    }
                } else if(event.which == 13) {      // click on "Enter" button
                    if(!$(document).find("div.clientlist-screen section.top-content span.next").hasClass('oe_hidden')){
                        $(document).find("div.clientlist-screen section.top-content span.next").click();
                    }
                } else if(event.which == 107) {     // click on numpad "+" button
                    $(document).find("div.clientlist-screen section.top-content span.new-customer").click();
                    $(document).find("div.clientlist-screen section.full-content section.client-details input.client-firstname").focus();
                    event.preventDefault();
                }
            }

            /* receipt screen key down events */
            if(!$($(document).find("div.receipt-screen")[0]).hasClass('oe_hidden')){
                if(event.which == 73){   // click on "i" button
                    $($(document).find("div.receipt-screen")[0]).find("div.print_invoice").trigger("click");
                } else if(event.which == 82){   // click on "r" button
                    $($(document).find("div.receipt-screen")[0]).find("div.print").trigger("click");
                } else if(event.which == 13){   // click on "Enter" button
                    $($(document).find("div.receipt-screen")[0]).find("div.top-content span.next").trigger("click");
                }
            }

            /* shortcut tips modal key down events */
            if(!$($(document).find("div.modal-dialog-shortcut-tips")[0]).hasClass('oe_hidden')){
                if(event.which == 27) {   // click on "Esc" button
                    $($(document).find("div.modal-dialog-shortcut-tips")[0]).find("footer.footer div.cancel").trigger("click");
                }
            }
        };
        $(document).find("body").on('keydown', this.product_screen_keydown_event_handler);
    },
    show: function () {
        this._super();
        var self = this;
        $("#shortcut_tips_btn").on("click", function (event) {
            self.gui.show_popup("shortcuttips");
        });
    }
});

/*--------------------------------------*\
|         THE PAYMENT SCREEN           |
\*======================================*/

screens.PaymentScreenWidget.include({
    order_is_valid: function(force_validation) {
    	var self = this;
        var order = this.pos.get_order();
		var customer = order.get_client();
		var amount = 0.0;
		var payment = order.is_paid()
		var lines = order.get_paymentlines();
		lines.forEach(function (line){
			amount = amount + line.amount;
		});
		if (!customer){
            this.gui.show_popup('confirm',{
                'title': _t('Please select the Customer'),
                'body': _t('You need to select the customer before you can invoice an order.'),
                confirm: function(){
                    self.gui.show_screen('clientlist', null, order);
                },
            });
            return false;
		}
		if (customer.vat == "9999999999999" && customer.limit_amount > 0.0 && amount > customer.limit_amount) {
            this.gui.show_popup('error',{
                title: _t('Order cannot be processed'),
                body:  _t('You cannot process the order if the Final Consumer the order amount is greater than USD 200. Select or create a customer'),
            });
            return false;
		}
        if (order.paymentlines.length === 0) {
            this.gui.show_popup('error',{
                'title': _t('Payment Methods'),
                'body':  _t('Please select a payment method.'),
            });
            return false;
        }
        if (!payment) {
            this.gui.show_popup('error',{
                'title': _t('Payment process'),
                'body':  _t('Fill in the amount to pay.'),
            });
            return false;
        }
		return this._super();
    },
    finalize_validation: function() {
        var self = this;
        var order = this.pos.get_order();

        if (order.is_paid_with_cash() && this.pos.config.iface_cashdrawer) { 

                this.pos.proxy.open_cashbox();
        }
        order.initialize_validation_date();
        order.finalized = true;
		this.pos.push_order(order);
        this.gui.show_screen('receipt');
    },
    
});


});
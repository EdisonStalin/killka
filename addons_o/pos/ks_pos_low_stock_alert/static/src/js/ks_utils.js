/*
    @Author: KSOLVES India Private Limited
    @Email: sales@ksolves.com
*/

odoo.define('ks_pos_low_stock_alert.utils', function (require) {
    "use strict";

    var _t = require('web.core')._t;

    function ks_validate_order_items_availability(ks_order, config, ks_gui) {

        var isValid = true, ks_order_line;

        if(!config.allow_out_of_stock) {
            for(var i = 0; i < ks_order.get_orderlines().length ; i++) {
                ks_order_line = ks_order.get_orderlines()[i];
                if(ks_order_line.get_product().type == 'product' && (ks_order_line.get_quantity() > ks_order_line.get_product().qty_available)) {
                    isValid = false;
                    break;
                }
            }
        }
        if(!isValid){
            ks_gui.show_popup('error',{
                'title': _t('Cannot order a product more than its availability'),
                'body':  _t('Realice el abastecimiento del producto, luego refresque la pantalla o presione F5, verifique antes que los pedidos estén enviados al sistema. \n ' + ks_order_line.get_product().display_name + ' solo tiene ' + ks_order_line.get_product().qty_available + ' elementos disponibles, esta intentando vender ' + ks_order_line.get_quantity() + ' producto(s).'),
            });
        }
        return isValid;
    }

    return {
        ks_validate_order_items_availability: ks_validate_order_items_availability
    }
});
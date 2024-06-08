odoo.define('oe_pos.BaseWidget', function(require) {
"use strict";

var field_utils = require('web.field_utils');
var utils = require('web.utils');
var base = require('point_of_sale.BaseWidget');
var round_di = utils.round_decimals;

base.include({
    format_currency: function(amount,precision,show=false){
        var currency = (this.pos && this.pos.currency) ? this.pos.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};

        amount = this.format_currency_no_symbol(amount,precision,show);

        if (currency.position === 'after') {
            return amount + ' ' + (currency.symbol || '');
        } else {
            return (currency.symbol || '') + ' ' + amount;
        }
    },
    format_currency_no_symbol: function(amount, precision, show=false) {
        var currency = (this.pos && this.pos.currency) ? this.pos.currency : {symbol:'$', position: 'after', rounding: 0.01, decimals: 2};
        var decimals = currency.decimals;

        if (show) {
            if (precision && this.pos.dp_show[precision] !== undefined) {
                decimals = this.pos.dp_show[precision];
            }
        }
        else {
            if (precision && this.pos.dp[precision] !== undefined) {
                decimals = this.pos.dp[precision];
            }
        }

        if (typeof amount === 'number') {
            amount = round_di(amount,decimals).toFixed(decimals);
            amount = field_utils.format.float(round_di(amount, decimals), {digits: [69, decimals]});
        }

        return amount;
    },
});
    
});
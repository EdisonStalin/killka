odoo.define('bo_kitchen_receipt_extend.multiprint', function (require) {
    "use strict";

    var models = require('point_of_sale.models');

    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        computeChanges: function(categories){
            var self = this;
            var res = _super_order.computeChanges.apply(this, arguments);
            
            var d = new Date();
            var month = '' + (d.getMonth() + 1);
                month = month.length < 2 ? ('0' + month) : month;
            var day = '' + d.getDate();
                day = day.length < 2 ? ('0' + day) : day;
            var full_date =  day + '/' + month + '/' + d.getFullYear()
            res.full_date = full_date;

            var cashier = self.pos.get_cashier();
            res.waiter = cashier ? cashier.name : null;

            return res;
        },
    });
    return models;
});

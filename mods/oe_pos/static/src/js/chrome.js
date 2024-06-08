odoo.define('oe_pos.chrome', function (require) {
"use strict";

var PosBaseWidget = require('point_of_sale.chrome');

PosBaseWidget.Chrome.include({
    renderElement:function () {
        var self = this;
        if(self.pos.config){
            if(self.pos.config.image){
                this.flag = 1
                this.a3 = window.location.origin + '/web/image?model=pos.config&field=image&id='+self.pos.config.id;
            }
        }
        this._super(this);
    },
});

});
odoo.define('web.UserSimulation', function (require) {
"use strict";

var SystrayMenu = require('web.SystrayMenu');
var session = require('web.session');
var Widget = require('web.Widget');
//var web_client = require('web.web_client');

var core = require('web.core');
var _t = core._t;

var UserSimulation = Widget.extend({
    template: "WebClient.UserSimulation",
    events: {
        "click a": "open_simulation_wizard"
    },
    open_simulation_wizard: function(ev){
        ev.preventDefault();
        this.do_action({
            res_model: 'user.simulation.wizard',
            name: _t('User Simulation'),
            views: [[false, 'form']],
            type: 'ir.actions.act_window',
            target: 'new',
        });
    },
    start: function () {
        return $.when(
            this._rpc({
                    model: 'res.users',
                    method: 'check_for_user_simulation',
                    kwargs: {'user_id':session.uid},
                }),
            this._super()
        ).then(function(result){
            if(!result){
                this.hide_simulation();
            }
        }.bind(this));
    },
    hide_simulation: function(){
        this.$el.html('');
    },
});

SystrayMenu.Items.push(UserSimulation);

});
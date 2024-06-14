// cambiar el menú del usuario
odoo.define('oe_web.UserMenu', function (require) {
	"use strict";
	var core = require('web.core');
	var _t = core._t;
	var _lt = core._lt;
	var QWeb = core.qweb;

	var UserMenu = require('web.UserMenu');
    var documentation_url = 'https://www.odoo.com/documentation/user';
    var support_url = 'https://www.odoo.com/buy';
    var account_url = 'https://accounts.odoo.com/account';

	UserMenu.include({
		init: function() {
			this._super.apply(this, arguments);
			var self = this;
			var session = this.getSession();
            self._rpc({
                model: 'res.company',
                method: 'search_read',
                domain: [['id','=',1]],
                fields: ['documentation_url','support_url','account_url'],
                lazy: false,
            }).then(function (res) {
                $.each(res, function (key, val) {
                    documentation_url = val.documentation_url;
                    support_url = val.support_url;
                    account_url = val.account_url;
                });
            })
		},
		
		// documentación
		_onMenuDocumentation: function () {
			window.open(documentation_url, '_blank');
		},
		// soporte
		_onMenuSupport: function () {
			window.open(support_url, '_blank');
		},
		// mi cuenta
		_onMenuAccount: function () {
			window.open(account_url, '_blank');
		},
	});
});

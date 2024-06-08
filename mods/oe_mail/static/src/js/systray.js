odoo.define('oe_mail.systray', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;

var ChatThread = require('mail.ChatThread');
var utils = require('mail.utils');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');

var name_software = 'Odoo';

var NotificationMenu = Widget.extend({
	template:'mail.chat.NotificationMenu',
	events: {
		'click .dropdown-toggle': 'start',
		'click .o_mail_request_permission': '_onRequestNotificationPermission',
		'click .o_request_permission_close': '_onCloseNotificationBar',
	},
    init: function () {
        this._super.apply(this, arguments);
        var self = this;
        this.notification_bar = (window.Notification && window.Notification.permission === "default");
        self._rpc({
            model: 'res.company',
            method: 'search_read',
            domain: [['id','=',1]],
            fields: ['name_software'],
            lazy: false,
        }).then(function (res) {
            $.each(res, function (key, val) {
            	name_software = val.name_software;
            });
        })
    },
    /**
     * @override
     */
    start: function () {
    	var defs = [];
    	this.thread = new ChatThread(this, {display_help: true});
        defs.push(this.thread.appendTo(this.$('.o_mail_navbar_item')));
        defs.push(this.thread.appendTo(this.$('.o_mail_navbar_dropdown')));
        if (this.notification_bar){
        	this.$(".o_mail_navbar_dropdown").slideDown();
        }
        return $.when.apply($, defs);
    },
    /**
     * @private
     */
    _onCloseNotificationBar: function () {
        this.$(".o_mail_navbar_dropdown").slideUp();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onRequestNotificationPermission: function (event) {
        var self = this;
        event.preventDefault();
        var def = window.Notification && window.Notification.requestPermission();
        if (def) {
            def.then(function (value) {
                if (value !== 'granted') {
                    utils.send_notification(self, _t('Permission denied'), name_software + _t(' will not have the permission to send native notifications on this device.'));
                } else {
                    utils.send_notification(self, _t('Permission granted'), name_software + _t(' has now the permission to send you native notifications on this device.'));
                }
            });
        }
        this.$(".o_mail_navbar_dropdown").slideUp();
        this.$(".dropdown-toggle").hide();
    },
	
});

SystrayMenu.Items.push(NotificationMenu);

});
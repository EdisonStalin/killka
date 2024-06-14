odoo.define('kw_matrix_widget.kw_matrix', function (require) {
    'use strict';

    var core = require('web.core');
    var field_registry = require('web.field_registry');
    var basicFields = require('web.basic_fields');

    var QWeb = core.qweb;

    var KwMatrixWidgetCls = basicFields.FieldText.extend({
        tag_template: "kw_matrix_widget_template",

        init: function () {
            this._super.apply(this, arguments);
            if (this.mode === 'edit') {
                this.tagName = 'div';
            }
            if (this.value) {
                this.set({
                    kw_matrix_data: JSON.parse(this.value),
                });
            } else {
                this.set({
                    kw_matrix_data: {},
                });
            }
        },

        start: function () {
            var self = this;
            if (self.setting) {
                return;
            }
            if (!this.get("kw_matrix_data")) {
                return;
            }
            this.renderElement();
        },

        renderElement: function () {
            this._super();
            this.$el.html(QWeb.render(
                "kw_matrix_widget_template",
                {"kw_matrix_data": this.get("kw_matrix_data")}));
            var self = this;
            this.$el.find(".clickable_matrix_cell").bind("click", function () {
                self.do_action(JSON.parse(atob($(this).data('matrix'))));
            });
        },

        reset: function (record, event) {
            var res = this._super(record, event);
            if (this.value) {
                this.set({
                    kw_matrix_data: JSON.parse(this.value),
                });
            } else {
                this.set({
                    kw_matrix_data: {},
                });
            }
            this.renderElement();
            return res;
        },

    });

    field_registry.add(
        'kw_matrix_widget', KwMatrixWidgetCls
    );
    return KwMatrixWidgetCls;
});

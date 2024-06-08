odoo.define('oe_web.many2one_clickable', function (require) {
    var ListRenderer = require('web.ListRenderer');
    var ListFieldMany2One = require('web.relational_fields').ListFieldMany2One;
    var rpc = require('web.rpc');

    ListRenderer.include({
        _renderBodyCell: function (record, node, colIndex, options) {
            if (!node.attrs.widget && node.attrs.name &&
                this.state.fields[node.attrs.name] &&
                this.state.fields[node.attrs.name].type === 'many2one') {
                // no explicit widget provided on a many2one field,
                // force `many2one` widget
                node.attrs.widget = 'many2one';
            }
            return this._super(record, node, colIndex, options);
        }
    });
    
    ListFieldMany2One.include({
        _renderReadonly: function () {
            this._super.apply(this, arguments);
            var self = this;

            if (!this.noOpen && this.value) {
                // Replace '<a>' element
                this.$el.removeClass("o_form_uri");
                this.$el = $("<span/>", {
                    html: this.$el.html(),
                    class: this.$el.attr("class") + " o_field_text",
                    name: this.$el.attr("name"),
                });

                // Append button
                var $a = $('<a/>', {
                    href: '#',
                    class: 'o_form_uri btn btn-sm btn-secondary' +
                           ' fa fa-angle-double-right many2one_clickable',
                    tabindex: '-1',
                }).on('click', function (ev) {
                    ev.preventDefault();
                    ev.stopPropagation();

                    rpc.query({
                        model: self.field.relation,
                        method: 'get_formview_action',
                        args: [[self.value.res_id]],
                    }).then(function (action) {
                        return self.do_action(action);
                    });
                });
                this.$el.append($a);
            }
        },

        getFocusableElement: function () {
            if (this.mode === 'readonly') {
                return $('');
            }
            return this._super.apply(this, arguments);
        },
    });

});
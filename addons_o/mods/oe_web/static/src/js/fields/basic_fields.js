odoo.define('oe_web.basic_fields', function (require) {
"use strict";
var field_registry = require('web.field_registry');
var basic_fields = require('web.basic_fields');
var FieldFloat = basic_fields.FieldFloat;
var Widget = require('web.Widget');

/*
 *extending the default float field
 */
var FieldPercent = FieldFloat.extend({

    // formatType is used to determine which format (and parse) functions
    formatType:'Percent',
    /**
     * to override to indicate which field types are supported by the widget
     *
     * @type Array<String>
     */
    supportedFieldTypes: ['float'],
});

//registering percent field
field_registry.add('Percent', FieldPercent);
return {
    FieldPercent: FieldPercent
};

});


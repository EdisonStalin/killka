odoo.define('oe_web.field_utils_format', function (require) {
"use strict";
var field_utils = require('web.field_utils');
var basic_controller = require('web.BasicController');
var _t = require('web.core')._t;
var error_val;

function formatPercent(value) {
	if(value){
		return value + "%";
	}
	else{
	    return 0.0 + "%";
	}
}

/**
 * Parse a String containing Percent in language formating
 *
 * @param {string} value
 *                The string to be parsed with the setting of thousands and
 *                decimal separator
 * @returns {float with percent symbol}
 * @throws {Error} if no float is found respecting the language configuration
 */
function parsePercent(value) {
    var lastChar = value[value.length -1];
    var parsed = value.slice(0, -1);
    if(value){
	    if(isNaN(parsed)){
	    	throw new Error(_.str.sprintf(core._t("'%s' is not a correct float"), value));
	    }
	    else
	    {
			if(lastChar != "%"){
				if(isNaN(lastChar)){
				    throw new Error(_.str.sprintf(core._t("'%s' is not a correct float"), value));
				}
				else
				{
				    if( value > 100 ||  value < 0 ){
				        throw new Error(_.str.sprintf(core._t("'%s' is not a correct float"), value));
				    }
				    else{
				        return value;
				    }
				}
			}
	        else
	        {
		        if( value.slice(0, -1) > 100 ||  value.slice(0, -1) < 0 ){
		            throw new Error(_.str.sprintf(core._t("'%s' is not a correct float"), value));
		        }
		        else
		        { 
		        	return parsed;
		        }
	        }
		}
    }
}

field_utils['format']['Percent'] = formatPercent;
field_utils['parse']['Percent'] = parsePercent;

/**
 * Parse a String containing Percent in language formating
 *
 * @param {string} value
 *                The string to be parsed with the setting of thousands and
 *                decimal separator
 * @returns {float with percent symbol}
 * @throws {Error} if no float is found respecting the language configuration
 */
basic_controller.include({
    _notifyInvalidFields: function (invalidFields) {
        var record = this.model.get(this.handle, {raw: true});
        var fields = record.fields;
        var self = this;
        var call_once = true;
        var if_percent = true;
        var errors = invalidFields.map(function (fieldName) {
            var fieldtype = fields[fieldName].type;
            if(fieldtype==="Percent" )
            {
                if_percent = false;
                self.do_warn(_t("Percent field value must be 0 to 100 only"));
            }
            if(call_once && if_percent)
            {
               call_once = false;
               self._super(invalidFields);
            }
        });
    }
})


});


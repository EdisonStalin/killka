odoo.define('oe_web.relational_fields', function (require) {
    "use strict";

    var rel_fields = require('web.relational_fields');
    var dialogs = require('web.view_dialogs');
    var core = require('web.core');
    var _t = core._t;

    rel_fields.FieldMany2One.include({
        _searchCreatePopup: function(view, ids, context) {
            var self = this;

            // Don't include already selected instances in the search domain
            var domain = self.record.getDomain({fieldName: self.name});
            if (self.field.type === 'many2many') {
                var selected_ids = self._getSearchBlacklist();
                if (selected_ids.length > 0) {
                    domain.push(['id', 'not in', selected_ids]);
                }
            }

            return new dialogs.SelectCreateDialog(self, _.extend({}, self.nodeOptions, {
                res_model: self.field.relation,
                domain: domain,
                context: _.extend({}, self.record.getContext(self.recordParams), context || {}),
                title: (view === 'search' ? _t("Search: ") : _t("Create: ")) + self.string,
                initial_ids: ids ? _.map(ids, function(x) {return x[0];}) : undefined,
                initial_view: view,
                disable_multiple_selection: self.field.type !== 'many2many',
                on_selected: function(records) {
                    if (self.field.type !== 'many2many') {
                        self.reinitialize(records[0]);
                    } else {
                        self.reinitialize(records);
                    }
                    self.activate();
                }
            })).open();
        },
	    /**
	     * @private
	     * @param {string} search_val
	     * @returns {Deferred}
	     */
	    _search: function (search_val) {
	        var self = this;
	        var def = $.Deferred();
	        this.orderer.add(def);
	
	        var context = this.record.getContext(this.recordParams);
	        var domain = this.record.getDomain(this.recordParams);
	
	        var blacklisted_ids = this._getSearchBlacklist();
	        if (blacklisted_ids.length > 0) {
	            domain.push(['id', 'not in', blacklisted_ids]);
	        }
	
	        this._rpc({
	            model: this.field.relation,
	            method: "name_search",
	            kwargs: {
	                name: search_val,
	                args: domain,
	                operator: "ilike",
	                limit: this.limit + 1,
	                context: context,
	            }})
	            .then(function (result) {
	                // possible selections for the m2o
	                var values = _.map(result, function (x) {
	                    x[1] = self._getDisplayName(x[1]);
	                    return {
	                        label: _.str.escapeHTML(x[1].trim()) || data.noDisplayContent,
	                        value: x[1],
	                        name: x[1],
	                        id: x[0],
	                    };
	                });
	
	                // search more... if more results than limit
	                if (values.length > self.limit) {
	                    values = values.slice(0, self.limit);
	                    values.push({
	                        label: _t("Search More..."),
	                        action: function () {
	                            self._rpc({
	                                    model: self.field.relation,
	                                    method: 'name_search',
	                                    kwargs: {
	                                        name: search_val,
	                                        args: domain,
	                                        operator: "ilike",
	                                        limit: 15000,
	                                        context: context,
	                                    },
	                                })
	                                .then(self._searchCreatePopup.bind(self, "search"));
	                        },
	                        classname: 'o_m2o_dropdown_option',
	                    });
	                }
	                var create_enabled = self.can_create && !self.nodeOptions.no_create;
	                // quick create
	                var raw_result = _.map(result, function (x) { return x[1]; });
	                if (create_enabled && !self.nodeOptions.no_quick_create &&
	                    search_val.length > 0 && !_.contains(raw_result, search_val)) {
	                    values.push({
	                        label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
	                            $('<span />').text(search_val).html()),
	                        action: self._quickCreate.bind(self, search_val),
	                        classname: 'o_m2o_dropdown_option'
	                    });
	                }
	                // create and edit ...
	                if (create_enabled && !self.nodeOptions.no_create_edit) {
	                    var createAndEditAction = function () {
	                        // Clear the value in case the user clicks on discard
	                        self.$('input').val('');
	                        return self._searchCreatePopup("form", false, self._createContext(search_val));
	                    };
	                    values.push({
	                        label: _t("Create and Edit..."),
	                        action: createAndEditAction,
	                        classname: 'o_m2o_dropdown_option',
	                    });
	                } else if (values.length === 0) {
	                    values.push({
	                        label: _t("No results to show..."),
	                    });
	                }
	
	                def.resolve(values);
	            });
	
	        return def;
	    },
    });
});

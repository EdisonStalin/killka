odoo.define('oe_web.backend', function (require) {
'use strict';

var FieldTextHtmlSimple = require('web_editor.backend').FieldTextHtmlSimple;

var ChatterComposerInherit = FieldTextHtmlSimple.include({
	
    /**
     * @private
     * @returns {Object} the summernote configuration
     */
    _getSummernoteConfig: function () {
        var summernoteConfig = {
            model: this.model,
            id: this.res_id,
            focus: false,
            height: 180,
            toolbar: [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['insert', this.nodeOptions['no-attachment'] ? ['link'] : ['link', 'picture']],
                ['history', ['undo', 'redo']]
            ],
            prettifyHtml: false,
            styleWithSpan: false,
            inlinemedia: ['p'],
            lang: "odoo",
            onChange: this._doDebouncedAction.bind(this),
            disableDragAndDrop: !!this.nodeOptions['no-attachment'],
        };

        var fieldNameAttachment =_.chain(this.recordData)
            .pairs()
            .find(function (value) {
                return _.isObject(value[1]) && value[1].model === "ir.attachment";
            })
            .first()
            .value();

        if (fieldNameAttachment) {
            this.fieldNameAttachment = fieldNameAttachment;
            this.attachments = [];
            summernoteConfig.onUpload = this._onUpload.bind(this);
        }
        summernoteConfig.getMediaDomain = this._getAttachmentsDomain.bind(this);


        summernoteConfig.toolbar.splice(7, 0, ['view', ['codeview']]);
        return summernoteConfig;
    },
	
});

return ChatterComposerInherit;

});
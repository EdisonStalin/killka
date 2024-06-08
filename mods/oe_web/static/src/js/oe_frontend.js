// datos predefinidos para los formularios del frontend 
$(function(){
	$('#login').val('admin');
	$('#lang').val($('[src="oe_web/static/src/js/oe_frontend.js"]').data('lang'));
	$('#country').val($('[src="/oe_web/static/src/js/oe_frontend.js"]').data('cc'));

	$('[autofocus]').removeAttr('autofocus');
	$('.o_database_create').on('shown.bs.modal', function() {
		$('[name="name"]:visible').focus().select();
	});

	$('#backup_file').on('change', function() {
		$('[name="name"]:visible').val($(this).val().replace(/^.*[\/\\][^a-zA-Z]*([a-zA-Z][a-zA-Z0-9_]*)[\._-].*$/gi, '$1').replace(/_\d+/g, '')).focus().select();
	});

	$('#backup_file').attr('accept', '.dump,.sql,.zip');
});
function validar_doc(nr) {
	var valid = false;

	if ((nr.length != 10) && (nr.length != 13))
		return false;
	
	if (nr.length == 13) {
		if (nr == '9999999999999') {
			valid = true;
		}
		else if (nr[2] == '9') {
			if (verifica_ruc_spri(nr))
				valid = true;
			else
				valid = true;
		}
		else if (nr[2] == '6' && verifica_ruc_spub(nr)) {
			valid = true;
		}
		else if (parseInt(nr[2]) < 6 && verifica_ruc_pnat(nr)){
			valid = true;
		}
	} 
	else if (verifica_cedula(nr)) {
		valid = true;
	}
	return valid;
}

function verifica_id_cons_final(nr) {
	for (k in nr)
		if (k != '9')
			return false;
	return true;
}

function verifica_ruc_spri(nr) {
	var state = parseInt(nr.substr(0, 2));
	
	var test1 = (state > 0 && state < 25);

	var test2 = (nr[2] == '9');

	var sum = parseInt(nr[0]) * 4;
	sum += parseInt(nr[1]) * 3;
	sum += parseInt(nr[2]) * 2;
	sum += parseInt(nr[3]) * 7;
	sum += parseInt(nr[4]) * 6;
	sum += parseInt(nr[5]) * 5;
	sum += parseInt(nr[6]) * 4;
	sum += parseInt(nr[7]) * 3;
	sum += parseInt(nr[8]) * 2;

	var veri = 11 - sum % 11;
	if (veri == 11)
		veri = 0;
	
	var test3 = (nr[9] == veri);

	var test4 = (parseInt(nr.substr(10, 3)) > 0);

	return (test1 && test2 && test3 && test4);
}

function verifica_ruc_spub(nr) {
	var state = parseInt(nr.substr(0, 2));
	
	var test1 = (state > 0 && state < 25);

	var test2 = (nr[2] == '6');

	var sum = parseInt(nr[0]) * 3;
	sum += parseInt(nr[1]) * 2;
	sum += parseInt(nr[2]) * 7;
	sum += parseInt(nr[3]) * 6;
	sum += parseInt(nr[4]) * 5;
	sum += parseInt(nr[5]) * 4;
	sum += parseInt(nr[6]) * 3;
	sum += parseInt(nr[7]) * 2;

	var veri = 11 - sum % 11;
	if (veri == 11)
		veri = 0;
	
	var test3 = (nr[8] == veri);

	var test4 = (parseInt(nr.substr(9, 4)) > 0);

	return (test1 && test2 && test3 && test4);
}

function verifica_ruc_pnat(nr) {
	var state = parseInt(nr.substr(0, 2));
	
	var test1 = (state > 0 && state < 25);

	var test2 = (parseInt(nr[2]) < 6);

	var test3 = verifica_cedula(nr);

	var test4 = (parseInt(nr.substr(10, 3)) > 0);

	return (test1 && test2 && test3 && test4);
}

function verifica_cedula(nr) {
	var x;
	if (nr == '9999999999')
		return false;

	var sum = 0;
	for (var i = 0; i < 9; i++) {
		x = parseInt(nr[i]) * (2 - i % 2);
		if (x > 9)
			sum += x - 9;
		else
			sum += x;
	}
	
	var veri = 10 - sum % 10;
	if (veri == 10)
		veri = 0;
	
	return (nr[9] == veri);
}
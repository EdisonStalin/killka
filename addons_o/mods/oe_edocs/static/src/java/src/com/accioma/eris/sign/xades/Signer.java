package com.accioma.eris.sign.xades;

import java.io.File;

public class Signer {

	public static void main(String[] args) {
		//String docfilename = null;
		String id2Sign = null;
		String name2Sign = null;
		String type2Sign = null;

		if( args.length < 1){
			System.out.println("Por favor especifique una accion");
			System.exit(0);
		}


		id2Sign = args[0];
		if(id2Sign.equals("comprobante")){
			name2Sign = "Comprobante";
			type2Sign = "text/xml";
		}
		else if(id2Sign.equals("lote")){
			name2Sign = "Lote";
			type2Sign = "text/xml";
		}

		try{

			File docFile = new File(new File(args[2]), args[1]);
			
			System.out.println("Proceso de Firma en JAVA: ");
			System.out.println("Firmando el archivo: " + args[1]);
			System.out.println("Ubicado en: " + docFile.getPath());
			System.out.println("Firma en: " + args[4]);
			System.out.println("Contrasena: " + args[5]);
			System.out.println("Guardar Firmado en: " + args[3]+args[1]);

			XAdESBESCoSignature signer = new XAdESBESCoSignature(docFile.getPath()
					, args[1]
					, args[3]
					, args[4]
					, args[5]
					, id2Sign
					, name2Sign
					, type2Sign
					);
			signer.execute();
			docFile.delete();
		}
		catch(Exception ex){
			System.out.println("ERROR JAVA: " + ex);
		}
		System.out.println("Cerrando aplicación JAVA");
		System.exit(0);
	}

}
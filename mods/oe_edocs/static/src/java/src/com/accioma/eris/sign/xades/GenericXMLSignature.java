package com.accioma.eris.sign.xades;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.IOException;
import java.io.StringWriter;
import java.security.KeyStore;
import java.security.KeyStoreException;
import java.security.NoSuchAlgorithmException;
import java.security.PrivateKey;
import java.security.Provider;
import java.security.UnrecoverableKeyException;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.util.Enumeration;
import java.util.List;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerException;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;

import org.w3c.dom.Document;
import org.xml.sax.SAXException;

import es.gob.jmulticard.ui.passwordcallback.a.e;
import es.mityc.firmaJava.libreria.utilidades.UtilidadTratarNodo;
import es.mityc.firmaJava.libreria.xades.DataToSign;
import es.mityc.firmaJava.libreria.xades.FirmaXML;
import es.mityc.javasign.issues.PassStoreKS;
import es.mityc.javasign.pkstore.CertStoreException;
import es.mityc.javasign.pkstore.IPKStoreManager;
import es.mityc.javasign.pkstore.IPassStoreKS;
import es.mityc.javasign.pkstore.keystore.KSStore;
import java.util.logging.Level;
import java.util.logging.Logger;

import static java.util.Objects.isNull;
import static java.util.Objects.nonNull;

/**
 * <p>
 * Clase base que deberían extender los diferentes ejemplos para realizar firmas
 * XML.
 * </p>
 * 
 */
public abstract class GenericXMLSignature {

	private static final String ID_CE_CERTIFICATE_POLICIES = "2.5.29.32";

    /**
     * <p>
     * Almacén PKCS12 con el que se desea realizar la firma
     * </p>
     */
    public InputStream PKCS12_RESOURCE;
    public String PKCS12_PASSWORD;
    public String OUTPUT_DIRECTORY;

    /**
     * <p>
     * Ejecución del ejemplo. La ejecución consistirá en la firma de los datos
     * creados por el método abstracto <code>createDataToSign</code> mediante el
     * certificado declarado en la constante <code>PKCS12_FILE</code>. El
     * resultado del proceso de firma será almacenado en un fichero XML en el
     * directorio correspondiente a la constante <code>OUTPUT_DIRECTORY</code>
     * del usuario bajo el nombre devuelto por el método abstracto
     * <code>getSignFileName</code>
     * </p>
     */
    
    public GenericXMLSignature(){
    	PKCS12_RESOURCE = null;
    	PKCS12_PASSWORD = null;
    	OUTPUT_DIRECTORY = null;
    }

    
    protected void execute() throws Exception {
    	KeyStore keyStore = getKeyStore();
    	if (keyStore == null) {
    		System.err.println("No se pudo obtener almacen de firma.");
            return;
    	}
    	String alias = getAlias(keyStore);

        // Obtencion del certificado para firmar. Utilizaremos el primer
        // certificado del almacen.
        X509Certificate certificate = (X509Certificate)keyStore.getCertificate(alias);
        if (certificate == null) {
            System.err.println("No existe ningún certificado para firmar.");
            return;
        }

        // Obtención de la clave privada asociada al certificado
        PrivateKey privateKey = null;
        KeyStore tmpKs = keyStore;
        try {
            privateKey = (PrivateKey)tmpKs.getKey(alias, PKCS12_PASSWORD.toCharArray());
        } catch (UnrecoverableKeyException ex) {
            Logger.getLogger(GenericXMLSignature.class.getName()).log(Level.SEVERE, null, ex);
        }

        // Obtención del provider encargado de las labores criptográficas
        Provider provider = keyStore.getProvider();

        /*
         * Creación del objeto que contiene tanto los datos a firmar como la
         * configuración del tipo de firma
         */
        DataToSign dataToSign = createDataToSign();

        /*
         * Creación del objeto encargado de realizar la firma
         */
        FirmaXML firma = new FirmaXML();

        // Firmamos el documento
        Document docSigned = null;
        try {
            Object[] res = firma.signFile(certificate, dataToSign, privateKey, provider);
            docSigned = (Document)res[0];
        } catch (Exception ex) {
            System.err.println("Error realizando la firma");
            ex.printStackTrace();
            return;
        }

        // Guardamos la firma a un fichero en el home del usuario
        String filePath = OUTPUT_DIRECTORY + File.separatorChar + getSignatureFileName();
        System.out.println("Firma salvada en en: " + filePath);
        saveDocumentToFile(docSigned, getSignatureFileName());
    }

    protected KeyStore getKeyStore() throws CertificateException {
    	KeyStore ks = null;
    	try
    	{
            ks = KeyStore.getInstance("PKCS12");
            ks.load(PKCS12_RESOURCE, PKCS12_PASSWORD.toCharArray());
        } catch (KeyStoreException ex) {
            System.err.println("No se puede generar KeyStore PKCS12");
            ex.printStackTrace();
            System.exit(-1);
        } catch (NoSuchAlgorithmException ex) {
            System.err.println("No se puede generar KeyStore PKCS12");
            ex.printStackTrace();
            System.exit(-1);
        } catch (CertificateException ex) {
            System.err.println("No se puede generar KeyStore PKCS12");
            ex.printStackTrace();
            System.exit(-1);
        } catch (IOException ex) {
            System.err.println("No se puede generar KeyStore PKCS12");
            ex.printStackTrace();
            System.exit(-1);
        }
        return ks;
    }
    
    
    private static String getAlias(KeyStore keyStore) {
    	String alias = null;
    	try {
    		Enumeration nombres = keyStore.aliases();
    		while (nombres.hasMoreElements()) {
    			String tmpAlias = (String)nombres.nextElement();
    			if (keyStore.isKeyEntry(tmpAlias)) {
    				alias = tmpAlias;
    			}
    		}
    	}
    	catch (KeyStoreException e) {
    		System.err.println("Error: " + e.getMessage());
    	}
    	return alias;
    }
    
        
    /**
     * <p>
     * Crea el objeto DataToSign que contiene toda la información de la firma
     * que se desea realizar. Todas las implementaciones deberán proporcionar
     * una implementación de este método
     * </p>
     * 
     * @return El objeto DataToSign que contiene toda la información de la firma
     *         a realizar
     */
    protected abstract DataToSign createDataToSign();

    /**
     * <p>
     * Nombre del fichero donde se desea guardar la firma generada. Todas las
     * implementaciones deberán proporcionar este nombre.
     * </p>
     * 
     * @return El nombre donde se desea guardar la firma generada
     */
    protected abstract String getSignatureFileName();

    /**
     * <p>
     * Escribe el documento a un fichero.
     * </p>
     * 
     * @param document
     *            El documento a imprmir
     * @param pathfile
     *            El path del fichero donde se quiere escribir.
     */
    private void saveDocumentToFile(Document document, String pathfile) {
        try {
            FileOutputStream fos = new FileOutputStream(pathfile);
            UtilidadTratarNodo.saveDocumentToOutputStream(document, fos, true);
        } catch (FileNotFoundException e) {
            System.err.println("Error al salvar el documento");
            e.printStackTrace();
            System.exit(-1);
        }
    }

    /**
     * <p>
     * Escribe el documento a un fichero. Esta implementacion es insegura ya que
     * dependiendo del gestor de transformadas el contenido podría ser alterado,
     * con lo que el XML escrito no sería correcto desde el punto de vista de
     * validez de la firma.
     * </p>
     * 
     * @param document
     *            El documento a imprmir
     * @param pathfile
     *            El path del fichero donde se quiere escribir.
     */
    @SuppressWarnings("unused")
    private void saveDocumentToFileUnsafeMode(Document document, String pathfile) {
        TransformerFactory tfactory = TransformerFactory.newInstance();
        Transformer serializer;
        try {
            serializer = tfactory.newTransformer();

            serializer.transform(new DOMSource(document), new StreamResult(new File(pathfile)));
        } catch (TransformerException e) {
            System.err.println("Error al salvar el documento");
            e.printStackTrace();
            System.exit(-1);
        }
    }

    /**
     * <p>
     * Devuelve el <code>Document</code> correspondiente al
     * <code>resource</code> pasado como parámetro
     * </p>
     * 
     * @param resource
     *            El recurso que se desea obtener
     * @return El <code>Document</code> asociado al <code>resource</code>
     */
    protected Document getDocument(String resource) {
        Document doc = null;
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        dbf.setNamespaceAware(true);
        try {
            doc = dbf.newDocumentBuilder().parse(this.getClass().getResourceAsStream(resource));
        } catch (ParserConfigurationException ex) {
            System.err.println("Error al parsear el documento");
            ex.printStackTrace();
            System.exit(-1);
        } catch (SAXException ex) {
            System.err.println("Error al parsear el documento");
            ex.printStackTrace();
            System.exit(-1);
        } catch (IOException ex) {
            System.err.println("Error al parsear el documento");
            ex.printStackTrace();
            System.exit(-1);
        } catch (IllegalArgumentException ex) {
            System.err.println("Error al parsear el documento");
            ex.printStackTrace();
            System.exit(-1);
        }
        return doc;
    }

    /**
     * <p>
     * Devuelve el contenido del documento XML
     * correspondiente al <code>resource</code> pasado como parámetro
     * </p> como un <code>String</code>
     * 
     * @param resource
     *            El recurso que se desea obtener
     * @return El contenido del documento XML como un <code>String</code>
     */
    protected String getDocumentAsString(String resource) {
        Document doc = getDocument(resource);
        TransformerFactory tfactory = TransformerFactory.newInstance();
        Transformer serializer;
        StringWriter stringWriter = new StringWriter();
        try {
            serializer = tfactory.newTransformer();
            serializer.transform(new DOMSource(doc), new StreamResult(stringWriter));
        } catch (TransformerException e) {
            System.err.println("Error al imprimir el documento");
            e.printStackTrace();
            System.exit(-1);
        }

        return stringWriter.toString();
    }

    /**
     * <p>
     * Devuelve el gestor de claves que se va a utilizar
     * </p>
     * 
     * @return El gestor de claves que se va a utilizar</p>
     */
    private IPKStoreManager getPKStoreManager() {
        IPKStoreManager storeManager = null;
        try {
            KeyStore ks = KeyStore.getInstance("PKCS12");
            ks.load(PKCS12_RESOURCE, PKCS12_PASSWORD.toCharArray());
            storeManager = new KSStore(ks, (IPassStoreKS) new PassStoreKS(PKCS12_PASSWORD));
        } catch (KeyStoreException ex) {
            System.err.println("No se puede generar KeyStore PKCS12");
            ex.printStackTrace();
            System.exit(-1);
        } catch (NoSuchAlgorithmException ex) {
            System.err.println("No se puede generar KeyStore PKCS12");
            ex.printStackTrace();
            System.exit(-1);
        } catch (CertificateException ex) {
            System.err.println("No se puede generar KeyStore PKCS12");
            ex.printStackTrace();
            System.exit(-1);
        } catch (IOException ex) {
            System.err.println("No se puede generar KeyStore PKCS12");
            ex.printStackTrace();
            System.exit(-1);
        }
        return storeManager;
    }

    /**
     * <p>
     * Recupera el primero de los certificados del almacén.
     * </p>
     * 
     * @param storeManager
     *            Interfaz de acceso al almacén
     * @return Primer certificado disponible en el almacén
     */
    private X509Certificate getFirstCertificate(final IPKStoreManager storeManager) throws Exception {
	    try {
    		List<X509Certificate> certs = storeManager.getSignCertificates();
			if (isNull(certs) || certs.isEmpty()) {
				throw new Exception("La lista de certificados se encuentra vacía.");
			}
            X509Certificate certificate = certs.stream().filter(this::hasCertificatePolicies).findFirst()
                    .orElseThrow(() -> new Exception("No se encontró ningún certificado con políticas"));
            return certificate;
        
	    } catch (CertStoreException ex) {
	        throw new Exception(ex);
	    } catch (Exception e) {
	        e.printStackTrace();
	    }
	    return null;
    }

	/**
	 * <p>
	 * Verifica la existencia de políticas en el certificado utilizando el campo
	 * <b>id-ce-certificatePolicies</b> con ID <b>2.5.29.32</b>.
	 * </p>
	 *
	 * @param certificate certificado a examinar
	 * @return true si encuentra políticas, false si no encuentra políticas o el certificado es nulo
	 */
	private boolean hasCertificatePolicies(X509Certificate certificate) {
		if (nonNull(certificate)) {
			byte[] certificatePolicies = certificate.getExtensionValue(ID_CE_CERTIFICATE_POLICIES);
            if (certificatePolicies != null && certificatePolicies.length > 0) {
                return true;
            }
		}
		return false;
	}
    
}
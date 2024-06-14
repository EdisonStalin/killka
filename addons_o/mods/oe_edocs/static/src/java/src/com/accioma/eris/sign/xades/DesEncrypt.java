package com.accioma.eris.sign.xades;

import java.io.IOException;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.PBEParameterSpec;

import Decoder.BASE64Decoder;
import Decoder.BASE64Encoder;

public class DesEncrypt {
	private static final char[] PASSWORD = "enfldsgbnlsngdlksdsgm".toCharArray();
	private static final byte[] SALT = {
        (byte) 0xde, (byte) 0x33, (byte) 0x10, (byte) 0x12,
        (byte) 0xde, (byte) 0x33, (byte) 0x10, (byte) 0x12,
    };
	
	public static String encrypt(String str) {
        try {
        	SecretKeyFactory keyFactory = SecretKeyFactory.getInstance("PBEWithMD5AndDES");
            SecretKey key = keyFactory.generateSecret(new PBEKeySpec(PASSWORD));
            Cipher pbeCipher = Cipher.getInstance("PBEWithMD5AndDES");
            pbeCipher.init(Cipher.ENCRYPT_MODE, key, new PBEParameterSpec(SALT, 20));
            return base64Encode(pbeCipher.doFinal(str.getBytes("UTF-8")));
        } catch (Exception e) {
        	e.printStackTrace();
        } 
        return null;
    }

	public static String decrypt(String str) {
        try {
        	SecretKeyFactory keyFactory = SecretKeyFactory.getInstance("PBEWithMD5AndDES");
            SecretKey key = keyFactory.generateSecret(new PBEKeySpec(PASSWORD));
            Cipher pbeCipher = Cipher.getInstance("PBEWithMD5AndDES");
            pbeCipher.init(Cipher.DECRYPT_MODE, key, new PBEParameterSpec(SALT, 20));
            return new String(pbeCipher.doFinal(base64Decode(str)), "UTF-8");
        } catch (Exception e) {
        	e.printStackTrace();
        } 
        return null;
    }
	
	private static String base64Encode(byte[] bytes) {
        // NB: This class is internal, and you probably should use another impl
		return new BASE64Encoder().encode(bytes);
        
    }
	
	private static byte[] base64Decode(String property) throws IOException {
        // NB: This class is internal, and you probably should use another impl
        return new BASE64Decoder().decodeBuffer(property);
    }


}

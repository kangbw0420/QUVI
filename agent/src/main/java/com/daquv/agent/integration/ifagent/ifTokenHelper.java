package com.daquv.agent.integration.ifagent;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.stereotype.Component;

import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.Key;
import java.security.MessageDigest;
import java.util.Base64;

@Slf4j
@Component
public class ifTokenHelper {

    private static final byte[] KEY_BUFF = "G9f#kL2!vT8zQ@e4Rb1X$dPw*Ny6J^am".getBytes();
    private static final byte[] IV_BUFF = "1234567890123456".getBytes();

    private static final String ENC = "AES/CBC/PKCS5Padding";
    private static final Key KEY = new SecretKeySpec(KEY_BUFF, "AES");
    private static final IvParameterSpec IV = new IvParameterSpec(IV_BUFF);

    /**
     * 토큰 생성에 필요한 정보를 담는 클래스
     */
    @Getter
    public static class TokenInfo {
        private String inttBizNo;
        private String inttCntrctId;

        public TokenInfo(String inttBizNo, String inttCntrctId) {
            this.inttBizNo = inttBizNo;
            this.inttCntrctId = inttCntrctId;
        }
    }

    /**
     * JWT 토큰 생성
     *
     * @param tokenInfo 토큰 생성에 필요한 정보
     * @return 생성된 JWT 토큰
     * @throws Exception 토큰 생성 중 오류 발생 시
     */
    public static String generateToken(TokenInfo tokenInfo) throws Exception {
        try {
            // Cipher 초기화
            Cipher encCipher = Cipher.getInstance(ENC);
            encCipher.init(Cipher.ENCRYPT_MODE, KEY, IV);

            // Header 생성
            ObjectMapper mapper = new ObjectMapper();

            ObjectNode header = mapper.createObjectNode();
            header.put("alg", "AS256");
            header.put("typ", "JWT");

            // Payload 생성
            ObjectNode payload = mapper.createObjectNode();
            payload.put("sub", tokenInfo.getInttBizNo() + "@" + tokenInfo.getInttCntrctId());
            payload.put("name", "webcash");
            payload.put("iat", System.currentTimeMillis());

            // Base64 인코딩
            String sHeader = Base64.getEncoder().encodeToString(
                    mapper.writeValueAsString(header).getBytes("UTF-8"));
            String sPayload = Base64.getEncoder().encodeToString(
                    mapper.writeValueAsString(payload).getBytes("UTF-8"));

            // 서명 생성
            byte[] signBuff = encCipher.doFinal((sHeader + "." + sPayload).getBytes("UTF-8"));

            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            String sSign = Base64.getEncoder().encodeToString(digest.digest(signBuff));

            // 최종 토큰 생성
            String token = sHeader + "." + sPayload + "." + sSign;

            log.debug("Token generated successfully for business: {}, 약정번호: {}",
                    tokenInfo.getInttBizNo(), tokenInfo.getInttCntrctId());

            return token;

        } catch (Exception e) {
            log.error("Failed to generate token for business: {}, 약정번호: {}",
                    tokenInfo.getInttBizNo(), tokenInfo.getInttCntrctId(), e);
            throw new Exception("토큰 생성 중 오류가 발생했습니다.", e);
        }
    }
}
package com.daquv.agent.cmmn.util;

import org.springframework.security.crypto.password.PasswordEncoder;
import lombok.extern.slf4j.Slf4j;

import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.security.spec.InvalidKeySpecException;
import java.util.Arrays;
import java.util.Base64;

@Slf4j
public class PythonCompatiblePasswordEncoder implements PasswordEncoder {

    private static final int ITERATIONS = 100_000;
    private static final int SALT_LENGTH = 32;
    private static final int HASH_LENGTH = 32;
    private static final String ALGORITHM = "PBKDF2WithHmacSHA256";

    @Override
    public String encode(CharSequence rawPassword) {
        try {
            // 32바이트 랜덤 salt 생성
            SecureRandom random = new SecureRandom();
            byte[] salt = new byte[SALT_LENGTH];
            random.nextBytes(salt);

            // PBKDF2로 해싱
            byte[] hash = pbkdf2(rawPassword.toString().toCharArray(), salt, ITERATIONS, HASH_LENGTH);

            // salt + hash를 Base64로 인코딩해서 저장
            byte[] combined = new byte[SALT_LENGTH + HASH_LENGTH];
            System.arraycopy(salt, 0, combined, 0, SALT_LENGTH);
            System.arraycopy(hash, 0, combined, SALT_LENGTH, HASH_LENGTH);

            return Base64.getEncoder().encodeToString(combined);

        } catch (Exception e) {
            log.error("비밀번호 인코딩 중 오류 발생", e);
            throw new RuntimeException("비밀번호 인코딩 실패", e);
        }
    }

    @Override
    public boolean matches(CharSequence rawPassword, String encodedPassword) {
        try {
            log.debug("비밀번호 검증 시작 - 입력된 해시: {}", encodedPassword);

            // Base64 디코딩
            byte[] combined = Base64.getDecoder().decode(encodedPassword);
            log.debug("디코딩된 바이트 길이: {}", combined.length);

            if (combined.length != SALT_LENGTH + HASH_LENGTH) {
                log.error("해시 길이가 올바르지 않음. 예상: {}, 실제: {}", SALT_LENGTH + HASH_LENGTH, combined.length);
                return false;
            }

            // salt와 저장된 hash 분리 (첫 32바이트 = salt, 나머지 32바이트 = hash)
            byte[] salt = new byte[SALT_LENGTH];
            byte[] storedHash = new byte[HASH_LENGTH];
            System.arraycopy(combined, 0, salt, 0, SALT_LENGTH);
            System.arraycopy(combined, SALT_LENGTH, storedHash, 0, HASH_LENGTH);

            log.debug("Salt (hex): {}", bytesToHex(salt));
            log.debug("저장된 해시 (hex): {}", bytesToHex(storedHash));

            // 입력된 비밀번호를 같은 salt로 해싱
            byte[] computedHash = pbkdf2(rawPassword.toString().toCharArray(), salt, ITERATIONS, HASH_LENGTH);
            log.debug("계산된 해시 (hex): {}", bytesToHex(computedHash));

            // 해시값 비교
            boolean matches = Arrays.equals(storedHash, computedHash);
            log.debug("비밀번호 일치 여부: {}", matches);

            return matches;

        } catch (Exception e) {
            log.error("비밀번호 검증 중 오류 발생", e);
            return false;
        }
    }

    /**
     * 바이트 배열을 16진수 문자열로 변환
     */
    private String bytesToHex(byte[] bytes) {
        StringBuilder result = new StringBuilder();
        for (byte b : bytes) {
            result.append(String.format("%02x", b));
        }
        return result.toString();
    }

    /**
     * PBKDF2 해싱 수행
     */
    private byte[] pbkdf2(char[] password, byte[] salt, int iterations, int keyLength)
            throws NoSuchAlgorithmException, InvalidKeySpecException {

        PBEKeySpec spec = new PBEKeySpec(password, salt, iterations, keyLength * 8);
        SecretKeyFactory skf = SecretKeyFactory.getInstance(ALGORITHM);
        return skf.generateSecret(spec).getEncoded();
    }

    /**
     * Python에서 생성된 해시가 특별한 형식인 경우를 위한 메소드
     * 필요에 따라 수정하세요
     */
    public boolean matchesWithPythonFormat(CharSequence rawPassword, String pythonEncodedPassword) {
        // Python에서 저장한 형식이 다르다면 여기서 처리
        // 예: "salt$hash" 형식이나 다른 구분자를 사용하는 경우
        return matches(rawPassword, pythonEncodedPassword);
    }
}
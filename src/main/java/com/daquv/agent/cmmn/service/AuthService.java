package com.daquv.agent.cmmn.service;

import com.daquv.agent.cmmn.dto.auth.UserResponseDto;
import com.daquv.agent.cmmn.entity.Users;
import com.daquv.agent.cmmn.dto.auth.LoginRequestDto;
import com.daquv.agent.cmmn.dto.auth.LoginResponseDto;
import com.daquv.agent.cmmn.repository.AuthRepository;
import com.daquv.agent.cmmn.util.JwtUtil;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.Arrays;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {
    private final AuthRepository authRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    @Value("${system.expire.date:}")
    private String systemExpireDate;

    @Value("${jwt.secret}")
    private String jwtSecret;

    @Value("${jwt.expiration:3600000}") // 기본값: 1시간 (밀리초)
    private long jwtExpiration;

    private static final List<String> VALID_ROLES = Arrays.asList("admin", "customer");
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyyMMdd");

    public LoginResponseDto login(LoginRequestDto requestDto) {
        try {
            String userId = requestDto.getUserId();
            String password = requestDto.getPassword();

            // 만료일 체크
            checkSystemExpiration();

            // 사용자 조회
            Users user = authRepository.findByUserId(userId)
                    .orElseThrow(() -> {
                        log.warn("사용자를 찾을 수 없음: {}", userId);
                        return new IllegalArgumentException("사용자를 찾을 수 없습니다: " + userId);
                    });

            // 역할 및 비밀번호 검증
            validateUserCredentials(user, password, userId);

            log.info("DB 인증 성공 (역할: {}): {}", user.getRole(), userId);

            String accessToken = jwtUtil.generateToken(userId, user.getRole());

            // LoginResponseDto 생성 및 반환 (토큰 포함)
            return LoginResponseDto.builder()
                    .access_token(accessToken)
                    .token_type("bearer")
                    .user_id(user.getUserId())
                    .role(user.getRole())
                    .company_id(user.getCompanyId())
                    .build();

        } catch (Exception e) {
            log.error("로그인 처리 중 오류 발생: {}", e.getMessage());
            throw e;
        }
    }

    private void checkSystemExpiration() {
        if (systemExpireDate != null && !systemExpireDate.trim().isEmpty()) {
            try {
                LocalDate expireDate = LocalDate.parse(systemExpireDate, DATE_FORMATTER);
                LocalDate currentDate = LocalDate.now();

                if (currentDate.isAfter(expireDate)) {
                    log.warn("시스템 만료됨: 만료일: {}", expireDate);
                    throw new RuntimeException("시스템이 사용 기한이 만료되었습니다. 다큐브에 문의 부탁드립니다.");
                }
            } catch (DateTimeParseException e) {
                log.error("잘못된 만료일 형식: {}", systemExpireDate);
                throw new RuntimeException("시스템 설정 오류가 발생했습니다.");
            }
        }
    }

    private void validateUserCredentials(Users user, String password, String userId) {
        String userRole = user.getRole();

        // 역할 검증
        if (!VALID_ROLES.contains(userRole)) {
            log.warn("권한 없음: {}, 역할: {}", userId, userRole);
            throw new RuntimeException("비즈플레이 인증에 실패했으며, 유효한 역할이 없습니다");
        }

        // 비밀번호 검증
        if (!passwordEncoder.matches(password, user.getUserPwd())) {
            log.warn("비밀번호 불일치: {}", userId);
            throw new RuntimeException("비밀번호가 일치하지 않습니다");
        }
    }


    public UserResponseDto getCurrentUser(String userId) {
        log.info("사용자 정보 조회: userId={}", userId);

        Users user = authRepository.findByUserId(userId)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다: " + userId));

        return new UserResponseDto(user);
    }
}

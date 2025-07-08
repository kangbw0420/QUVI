package com.daquv.agent.cmmn.util;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.http.Cookie;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.ArrayList;

@Slf4j
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    @Autowired
    private JwtUtil jwtUtil;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        String requestURI = request.getRequestURI();
        log.debug("JWT 필터 실행 - URI: {}", requestURI);

        try {
            // 1. Authorization 헤더에서 토큰 추출 (우선순위)
            String token = extractTokenFromHeader(request);

            // 2. 헤더에 없으면 쿠키에서 토큰 추출
            if (token == null) {
                token = extractTokenFromCookie(request);
                log.debug("쿠키에서 토큰 추출 시도");
            } else {
                log.debug("Authorization 헤더에서 토큰 추출");
            }

            if (token != null && jwtUtil.validateToken(token)) {
                String username = jwtUtil.extractUsername(token);
                String userRole = jwtUtil.extractUserRole(token);

                log.debug("토큰 검증 성공 - username: {}, role: {}", username, userRole);

                if (username != null && SecurityContextHolder.getContext().getAuthentication() == null) {
                    // UserDetails 생성
                    UserDetails userDetails = createUserDetails(username, userRole);

                    // Authentication 객체 생성
                    UsernamePasswordAuthenticationToken authentication =
                            new UsernamePasswordAuthenticationToken(userDetails, null, userDetails.getAuthorities());

                    // SecurityContext에 설정
                    SecurityContextHolder.getContext().setAuthentication(authentication);

                    log.info("JWT 인증 성공: username={}, role={}", username, userRole);
                }
            } else {
                log.debug("토큰이 없거나 유효하지 않음");
            }
        } catch (Exception e) {
            log.error("JWT 인증 필터 오류: {}", e.getMessage(), e);
        }

        filterChain.doFilter(request, response);
    }

    // Authorization 헤더에서 토큰 추출 (새로 추가)
    private String extractTokenFromHeader(HttpServletRequest request) {
        String authHeader = request.getHeader("Authorization");
        log.debug("Authorization 헤더: {}", authHeader);

        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            String token = authHeader.substring(7);
            log.debug("Bearer 토큰 추출: {}...", token.substring(0, Math.min(token.length(), 10)));
            return token;
        }
        return null;
    }

    // 기존 쿠키 추출 메서드 유지
    private String extractTokenFromCookie(HttpServletRequest request) {
        Cookie[] cookies = request.getCookies();
        if (cookies != null) {
            for (Cookie cookie : cookies) {
                if ("session_token".equals(cookie.getName())) {
                    log.debug("쿠키에서 토큰 추출: {}...", cookie.getValue().substring(0, Math.min(cookie.getValue().length(), 10)));
                    return cookie.getValue();
                }
            }
        }
        return null;
    }

    private UserDetails createUserDetails(String username, String role) {
        return new org.springframework.security.core.userdetails.User(
                username,
                "", // password는 JWT에서 이미 검증됨
                new ArrayList<>() // authorities는 RoleAspect에서 처리
        );
    }
}
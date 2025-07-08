package com.daquv.agent.cmmn.controller;

import com.daquv.agent.cmmn.dto.auth.LoginRequestDto;
import com.daquv.agent.cmmn.dto.auth.LoginResponseDto;
import com.daquv.agent.cmmn.dto.auth.UserResponseDto;
import com.daquv.agent.cmmn.service.AuthService;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;

import com.daquv.agent.cmmn.util.JwtUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
public class AuthController {

    @Autowired
    private AuthService authService;

    @Autowired
    private JwtUtil jwtUtil;

    @PostMapping("/login")
    public ResponseEntity<LoginResponseDto> login(@Valid @RequestBody LoginRequestDto requestDto) {
        log.info("받은 요청: userId={}, userPwd={}", requestDto.getUserId(), requestDto.getPassword());
        LoginResponseDto responseDto = authService.login(requestDto);

        return ResponseEntity.ok(responseDto);
    }

    @GetMapping("/users/me")
    public ResponseEntity<UserResponseDto> getCurrentUser(HttpServletRequest request) {
        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return ResponseEntity.status(401).build();
        }

        String token = authHeader.substring(7);

        // JWT에서 사용자 ID 추출 (JwtUtil 필요)
        String userId = jwtUtil.getUserIdFromToken(token);

        UserResponseDto userDto = authService.getCurrentUser(userId);
        return ResponseEntity.ok(userDto);
    }
}

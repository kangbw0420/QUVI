package com.daquv.agent.cmmn.controller;

import com.daquv.agent.cmmn.util.JwtUtil;
import com.daquv.agent.cmmn.dto.utterance.CreateUtteranceRequestDto;
import com.daquv.agent.cmmn.dto.utterance.CreateUtteranceResponseDto;
import com.daquv.agent.cmmn.dto.utterance.GetHistoryResponseDto;
import com.daquv.agent.cmmn.dto.utterance.GetRecommendQuestionResponseDto;
import com.daquv.agent.cmmn.service.UtteranceService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletRequest;
import javax.validation.Valid;

@RequiredArgsConstructor
@RestController
@Slf4j
public class UtteranceController {
    private final UtteranceService utteranceService;
    private final JwtUtil jwtUtil;


    @PostMapping("/save_history")
    public ResponseEntity<CreateUtteranceResponseDto> saveUtterance(
            @Valid @RequestBody CreateUtteranceRequestDto requestDto,
            HttpServletRequest request) {

        try {
            log.info("발화 기록 저장 요청: {}", requestDto);

            // Authorization 헤더에서 JWT 토큰 추출
            String authHeader = request.getHeader("Authorization");
            if (authHeader == null || !authHeader.startsWith("Bearer ")) {
                return ResponseEntity.status(401)
                        .body(new CreateUtteranceResponseDto("error", "인증 토큰이 필요합니다.", null));
            }

            String token = authHeader.substring(7);
            String currentUserId = jwtUtil.getUserIdFromToken(token); // JWT 유틸 필요

            log.info("현재 사용자: {}", currentUserId);

            // 발화 기록 저장
            CreateUtteranceResponseDto response = utteranceService.saveUserHistory(
                    currentUserId,
                    requestDto.getUtteranceContents(),
                    requestDto.getCompanyId()
            );

            return ResponseEntity.ok(response);

        } catch (IllegalArgumentException e) {
            log.error("잘못된 요청: {}", e.getMessage());
            return ResponseEntity.badRequest()
                    .body(new CreateUtteranceResponseDto("error", e.getMessage(), null));

        } catch (Exception e) {
            log.error("발화 기록 저장 중 오류 발생", e);
            return ResponseEntity.status(500)
                    .body(new CreateUtteranceResponseDto("error", "서버 내부 오류가 발생했습니다.", null));
        }
    }

    @GetMapping("/history")
    public ResponseEntity<GetHistoryResponseDto> getHistory(
            @RequestParam(required = false) String companyId,
            HttpServletRequest request){

        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return ResponseEntity.status(401)
                    .body(new GetHistoryResponseDto("error", null));
        }

        String token = authHeader.substring(7);
        String currentUserId = jwtUtil.getUserIdFromToken(token);

        GetHistoryResponseDto responseDto = utteranceService.getAllHistory(currentUserId, companyId);

        return ResponseEntity.ok(responseDto);
    }

    @GetMapping("/recommend")
    public ResponseEntity<GetRecommendQuestionResponseDto> getRecommendQuestion(
            HttpServletRequest request,
            @RequestParam(required = false) String companyId
    ) {
        try {
            String authHeader = request.getHeader("Authorization");
            if (authHeader == null || !authHeader.startsWith("Bearer ")) {
                return ResponseEntity.status(401)
                        .body(new GetRecommendQuestionResponseDto("error", null));
            }

            String token = authHeader.substring(7);
            String currentUserId = jwtUtil.getUserIdFromToken(token);

            log.info("추천 질문 조회 요청 - userId: {}, companyId: {}", currentUserId, companyId);

            // 현재 사용자의 회사 ID 가져오기 (Python의 current_user.company_id와 동일)
            GetRecommendQuestionResponseDto responseDto = utteranceService.getRecommends(currentUserId, companyId);

            return ResponseEntity.ok(responseDto);

        } catch (Exception e) {
            log.error("추천 질문 조회 중 오류 발생", e);
            return ResponseEntity.status(500)
                    .body(new GetRecommendQuestionResponseDto("error", null));
        }
    }
}

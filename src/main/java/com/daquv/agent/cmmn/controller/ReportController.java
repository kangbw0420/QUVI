package com.daquv.agent.cmmn.controller;

import com.daquv.agent.cmmn.dto.report.ChangeReportRequestDto;
import com.daquv.agent.cmmn.dto.report.ChangeReportResponseDto;
import com.daquv.agent.cmmn.dto.report.SaveReportsRequestDto;
import com.daquv.agent.cmmn.dto.report.SaveReportsResponseDto;
import com.daquv.agent.cmmn.service.ReportService;
import com.daquv.agent.cmmn.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import javax.servlet.http.HttpServletRequest;

@RestController
@RequiredArgsConstructor
public class ReportController {
    private final ReportService reportService;
    private final JwtUtil jwtUtil;

    @PostMapping("/report")
    public ResponseEntity<SaveReportsResponseDto> saveReport(
            @RequestBody SaveReportsRequestDto requestDto,
            HttpServletRequest request) {
        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return ResponseEntity.status(401).build();
        }

        String token = authHeader.substring(7);

        String userId = jwtUtil.getUserIdFromToken(token);

        SaveReportsResponseDto responseDto = reportService.saveUserReport(requestDto, userId);

        return ResponseEntity.ok(responseDto);
    }

    @PostMapping("/save_data_changes")
    public ResponseEntity<ChangeReportResponseDto> saveDataChanges(
            @RequestBody ChangeReportRequestDto requestDto,
            HttpServletRequest request
    ) {
        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return ResponseEntity.status(401).build();
        }

        String token = authHeader.substring(7);

        String userId = jwtUtil.getUserIdFromToken(token);

        ChangeReportResponseDto responseDto = reportService.processDataChange(requestDto, userId);

        return ResponseEntity.ok(responseDto);
    }
}

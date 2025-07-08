package com.daquv.agent.cmmn.controller;

import com.daquv.agent.cmmn.dto.mapping.GetMappingResponseDto;
import com.daquv.agent.cmmn.service.MappingService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RequiredArgsConstructor
@RestController
@Slf4j
public class MappingController {

    private final MappingService mappingService;

    @GetMapping("/mapping/getAll")
    public ResponseEntity<GetMappingResponseDto> getAllMapping() {
        GetMappingResponseDto responseDto = mappingService.getAll();

        return ResponseEntity.ok(responseDto);
    }
}

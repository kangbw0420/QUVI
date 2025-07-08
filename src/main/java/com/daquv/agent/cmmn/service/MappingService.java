package com.daquv.agent.cmmn.service;


import com.daquv.agent.cmmn.dto.mapping.GetMappingResponseDto;
import com.daquv.agent.cmmn.entity.TitleMapping;
import com.daquv.agent.cmmn.repository.MappingRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

@Service
@Slf4j
@RequiredArgsConstructor
public class MappingService {

    private final MappingRepository mappingRepository;
    private static final DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    public GetMappingResponseDto getAll() {
        List<TitleMapping> mappings = mappingRepository.findAll();

        List<GetMappingResponseDto.Data> mappingDataList = mappings.stream()
                .map(mapping -> new GetMappingResponseDto.Data(
                        mapping.getIdx(),
                        mapping.getOriginalTitle(),
                        mapping.getReplaceTitle(),
                        mapping.getType(),
                        mapping.getAlign(),
                        mapping.getRegDtm().format(formatter)
                ))
                .collect(Collectors.toList());
        return new GetMappingResponseDto(mappingDataList);
    }
}

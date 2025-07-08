package com.daquv.agent.cmmn.dto.utterance;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Getter
public class GetRecommendQuestionResponseDto {
    private String status;
    private List<String> recommend;
}

package com.daquv.agent.cmmn.dto.utterance;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CreateUtteranceResponseDto {
    private String status;
    private String message;
    private Object data;
}

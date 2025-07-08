package com.daquv.agent.cmmn.dto.utterance;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import javax.validation.constraints.NotNull;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CreateUtteranceRequestDto {

    @NotNull(message = "utterance_contents는 필수 항목입니다.")
    @JsonProperty("utterance_contents")
    private String utteranceContents;

    @JsonProperty("company_id")
    private String companyId;
}

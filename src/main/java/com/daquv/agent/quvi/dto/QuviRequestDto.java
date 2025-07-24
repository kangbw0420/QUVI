package com.daquv.agent.quvi.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class QuviRequestDto {
    @JsonProperty("user_question")
    private String userQuestion;

    @JsonProperty("company_id")
    private String companyId = "aicfo_dev";

    @JsonProperty("user_id")
    private String userId = "qv_id";

    @JsonProperty("session_id")
    private String sessionId = "";

    @JsonProperty("use_intt_id")
    private String useInttId;
}

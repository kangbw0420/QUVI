package com.daquv.agent.cmmn.dto.auth;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
@Data
public class LoginRequestDto {
    @JsonProperty("user_id")
    private String userId;

    private String password;
}


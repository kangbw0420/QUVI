package com.daquv.agent.cmmn.dto.auth;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class LoginResponseDto {
    private String access_token;

    private String token_type;

    private String user_id;

    private String company_id;

    private String role;
}

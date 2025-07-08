package com.daquv.agent.cmmn.dto.auth;

import com.daquv.agent.cmmn.entity.Users;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UserResponseDto {
    private String userId;
    private String userNm;
    private String role;
    private String companyId;

    public UserResponseDto(Users user) {
        this.userId = user.getUserId();
        this.userNm = user.getUserNm();
        this.role = user.getRole();
        this.companyId = user.getCompanyId();
    }
}
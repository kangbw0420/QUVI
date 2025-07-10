package com.daquv.agent.workflow.dto;

import lombok.*;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString
public class UserInfo {
    private String userId;
    private String companyId;
    private String useInttId;
    
    /**
     * Python의 Tuple[str, str] 형태로 변환
     */
    public String[] toArray() {
        return new String[]{userId, companyId, useInttId};
    }
    
    /**
     * 배열에서 UserInfo 생성
     */
    public static UserInfo fromArray(String[] array) {
        if (array == null || array.length < 3) {
            return null;
        }
        return UserInfo.builder()
                .userId(array[0])
                .companyId(array[1])
                .useInttId(array[2])
                .build();
    }
} 
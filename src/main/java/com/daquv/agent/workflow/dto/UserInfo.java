package com.daquv.agent.workflow.dto;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.*;

import java.util.Arrays;
import java.util.List;

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
     * Python의 List[str] 형태로 변환
     */
    public List<String> toArray() {
        String actualUserId = userId;
        if (userId != null && userId.startsWith("{") && userId.contains("\"id\"")) {
            try {
                ObjectMapper mapper = new ObjectMapper();
                JsonNode jsonNode = mapper.readTree(userId);
                actualUserId = jsonNode.get("id").asText();
            } catch (Exception e) {
                // JSON 파싱 실패시 원본 사용
                actualUserId = userId;
            }
        }
        return Arrays.asList(actualUserId, useInttId);
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
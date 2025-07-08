package com.daquv.agent.cmmn.dto.mapping;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

@NoArgsConstructor
@AllArgsConstructor
@Getter
public class GetMappingResponseDto {
    private List<Data> data;

    @NoArgsConstructor
    @AllArgsConstructor
    @Getter
    public static class Data {
        private Long idx;
        private String original_title;
        private String replace_title;
        private String type;
        private String align;
        private String reg_dtm;
    }
}

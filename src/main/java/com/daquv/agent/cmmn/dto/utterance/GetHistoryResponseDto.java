package com.daquv.agent.cmmn.dto.utterance;

import lombok.*;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Getter
public class GetHistoryResponseDto {

    private String status;
    private List<HistoryData> result;



    @Getter
    @NoArgsConstructor
    @AllArgsConstructor
    public static class HistoryData{
        private String utterance_contents;
        private String utterance_date;
    }

}

package com.daquv.agent.workflow.dto;

import lombok.*;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@ToString
public class VectorNotes {
    private String originNote;
    private List<String> vectorNotes;
} 
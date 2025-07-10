package com.daquv.agent.workflow.prompt;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class PromptTemplate {
    private final String template;
    private final StringBuilder systemPrompt = new StringBuilder();
    private final List<ChatMessage> fewShotMessages = new ArrayList<>();
    private final List<ChatMessage> historyMessages = new ArrayList<>();
    private String userMessage = "";

    public PromptTemplate(String template) {
        this.template = template;
    }

    public static PromptTemplate fromFile(String fileName) {
        try {
            // 클래스패스에서 리소스 읽기
            String resourcePath = "prompts/" + fileName + ".prompt";
            java.io.InputStream inputStream = PromptTemplate.class.getClassLoader().getResourceAsStream(resourcePath);
            if (inputStream == null) {
                throw new RuntimeException("프롬프트 파일을 찾을 수 없습니다: " + resourcePath);
            }
            
            // Java 8 호환 방식으로 바이트 배열 읽기
            java.io.ByteArrayOutputStream buffer = new java.io.ByteArrayOutputStream();
            int nRead;
            byte[] data = new byte[1024];
            while ((nRead = inputStream.read(data, 0, data.length)) != -1) {
                buffer.write(data, 0, nRead);
            }
            buffer.flush();
            byte[] bytes = buffer.toByteArray();
            
            String content = new String(bytes, StandardCharsets.UTF_8);
            inputStream.close();
            return new PromptTemplate(content);
        } catch (IOException e) {
            throw new RuntimeException("프롬프트 파일을 읽을 수 없습니다: " + fileName, e);
        }
    }

    public static PromptTemplate from(String template) {
        return new PromptTemplate(template);
    }

    public String getTemplate() {
        return template;
    }

    // 기본적인 치환 메서드 (범용적)
    public String replace(String placeholder, String value) {
        return template.replace(placeholder, value);
    }

    // 여러 치환을 한번에
    public String replaceAll(String... replacements) {
        String result = template;
        for (int i = 0; i < replacements.length; i += 2) {
            if (i + 1 < replacements.length) {
                result = result.replace(replacements[i], replacements[i + 1]);
            }
        }
        return result;
    }

    // format 메서드들 (하위 호환성)
    public String format(String userQuestion) {
        return template.replace("{user_question}", userQuestion);
    }

    public String format(String userQuestion, String columnList, String sqlQuery) {
        return template
            .replace("{user_question}", userQuestion)
            .replace("{column_list}", columnList)
            .replace("{sql_query}", sqlQuery);
    }

    public String format(String userQuestion, String draftAnswer) {
        return template
            .replace("{user_question}", userQuestion)
            .replace("{draft_answer}", draftAnswer);
    }

    // 새로운 프롬프트 구성 메서드들

    /**
     * 시스템 프롬프트 설정
     */
    public PromptTemplate withSystemPrompt(String systemPrompt) {
        this.systemPrompt.setLength(0);
        this.systemPrompt.append(systemPrompt);
        return this;
    }

    /**
     * Few-shot 예제 추가 (human, ai 쌍)
     */
    public PromptTemplate withFewShot(String human, String ai) {
        fewShotMessages.add(new ChatMessage("human", human));
        fewShotMessages.add(new ChatMessage("ai", ai));
        return this;
    }

    /**
     * Few-shot 예제 리스트 추가
     */
    public PromptTemplate withFewShots(List<Map<String, Object>> fewShots) {
        for (Map<String, Object> shot : fewShots) {
            String input = (String) shot.get("input");
            String output = (String) shot.get("output");
            if (input != null && output != null) {
                // 날짜 정보가 있으면 질문에 추가
                if (shot.containsKey("date")) {
                    String date = (String) shot.get("date");
                    input = input + ", 오늘: " + date + ".";
                }
                
                fewShotMessages.add(new ChatMessage("human", input));
                fewShotMessages.add(new ChatMessage("ai", output));
            }
        }
        return this;
    }

    /**
     * Few-shot 예제 리스트 추가 (날짜 정보 제외)
     */
    public PromptTemplate withFewShotsWithoutDateModification(List<Map<String, Object>> fewShots) {
        if (fewShots != null) {
            for (Map<String, Object> shot : fewShots) {
                String input = (String) shot.get("input");
                String output = (String) shot.get("output");
                if (input != null && output != null) {
                    fewShotMessages.add(new ChatMessage("human", input));
                    fewShotMessages.add(new ChatMessage("ai", output));
                }
            }
        }
        return this;
    }

    /**
     * Dater 전용 Few-shot 처리 메서드
     * 기존 withFewShots()와 유사하지만, output을 JSON 형태로 감쌉니다.
     */
    public PromptTemplate withFewShotsForDater(List<Map<String, Object>> fewShots) {
        if (fewShots != null) {
            for (Map<String, Object> shot : fewShots) {
                String input = (String) shot.get("input");
                String output = (String) shot.get("output");
                if (input != null && output != null) {
                    // 기존 withFewShots()와 동일하게 날짜 정보가 있으면 질문에 추가
                    if (shot.containsKey("date")) {
                        String date = (String) shot.get("date");
                        input = input + ", 오늘: " + date + ".";
                    }

                    // Dater 전용: output을 JSON 형태로 감쌈
                    String formattedOutput = "{" + output + "}";

                    fewShotMessages.add(new ChatMessage("human", input));
                    fewShotMessages.add(new ChatMessage("ai", formattedOutput));
                }
            }
        }
        return this;
    }

    /**
     * Chat history 리스트 추가
     */
    public PromptTemplate withHistory(List<Map<String, Object>> history) {
        for (Map<String, Object> item : history) {
            String userQuestion = (String) item.get("user_question");
            String finalAnswer = (String) item.get("final_answer");
            if (userQuestion != null && finalAnswer != null) {
                historyMessages.add(new ChatMessage("human", userQuestion));
                historyMessages.add(new ChatMessage("ai", finalAnswer));
            }
        }
        return this;
    }

    /**
     * Chat history 추가 (human, ai 쌍)
     */
    public PromptTemplate withHistory(String human, String ai) {
        historyMessages.add(new ChatMessage("human", human));
        historyMessages.add(new ChatMessage("ai", ai));
        return this;
    }

    /**
     * 사용자 메시지 설정
     */
    public PromptTemplate withUserMessage(String userMessage) {
        this.userMessage = userMessage;
        return this;
    }

    /**
     * 완성된 프롬프트 생성
     */
    public String build() {
        StringBuilder fullPrompt = new StringBuilder();
        
        // 시스템 프롬프트
        if (systemPrompt.length() > 0) {
            fullPrompt.append(systemPrompt.toString()).append("\n\n");
        }
        
        // Few-shot 메시지들
        for (ChatMessage message : fewShotMessages) {
            fullPrompt.append(message.role).append(": ").append(message.content).append("\n");
        }
        
        // Few-shot과 history 사이에 구분자 추가
        if (!fewShotMessages.isEmpty() && !historyMessages.isEmpty()) {
            fullPrompt.append("\n");
        }
        
        // History 메시지들
        for (ChatMessage message : historyMessages) {
            fullPrompt.append(message.role).append(": ").append(message.content).append("\n");
        }
        
        // History와 사용자 메시지 사이에 구분자 추가
        if (!historyMessages.isEmpty() && !userMessage.isEmpty()) {
            fullPrompt.append("\n");
        }
        
        // 사용자 메시지
        if (!userMessage.isEmpty()) {
            fullPrompt.append("human: ").append(userMessage);
        }
        
        return fullPrompt.toString();
    }

    /**
     * 프롬프트 구성 정보 초기화
     */
    public PromptTemplate clear() {
        systemPrompt.setLength(0);
        fewShotMessages.clear();
        historyMessages.clear();
        userMessage = "";
        return this;
    }

    /**
     * Chat 메시지 내부 클래스
     */
    private static class ChatMessage {
        final String role;
        final String content;

        ChatMessage(String role, String content) {
            this.role = role;
            this.content = content;
        }
    }
}
package com.daquv.agent.workflow.semanticquery.utils;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component
@Slf4j
@RequiredArgsConstructor
public class ResponseParser {

    private final ObjectMapper objectMapper;

    /**
     * LLM 응답을 Map으로 파싱 (Python의 ast.literal_eval 대체)
     * @param response LLM 응답 문자열
     * @return 파싱된 Map 객체
     */
    public Map<String, Object> parseResponse(String response) {
        try {
            log.debug("Original response: {}", response);
            String cleaned = preprocessResponse(response);
            log.debug("Cleaned response: {}", cleaned);

            // JSON 유효성 사전 검증
            if (!isValidJsonFormat(cleaned)) {
                log.warn("Invalid JSON format detected, attempting repair: {}", cleaned);
                cleaned = repairJsonFormat(cleaned);
                log.debug("Repaired JSON: {}", cleaned);
            }

            TypeReference<Map<String, Object>> typeRef = new TypeReference<Map<String, Object>>() {};
            return objectMapper.readValue(cleaned, typeRef);
        } catch (Exception e) {
            log.error("Failed to parse response. Original: {}, Cleaned: {}", response, preprocessResponse(response), e);
            throw new RuntimeException("Failed to parse response: " + response, e);
        }
    }

    /**
     * JSON 형식이 올바른지 기본 검증
     */
    private boolean isValidJsonFormat(String json) {
        if (json == null || json.trim().isEmpty()) {
            return false;
        }

        String trimmed = json.trim();

        // 기본적인 JSON 구조 확인
        boolean startsCorrectly = trimmed.startsWith("{") || trimmed.startsWith("[");
        boolean endsCorrectly = trimmed.endsWith("}") || trimmed.endsWith("]");

        return startsCorrectly && endsCorrectly;
    }

    /**
     * 손상된 JSON을 수리하는 메서드
     */
    private String repairJsonFormat(String json) {
        String repaired = json.trim();

        // 이중 중괄호 문제가 있는 경우 더 적극적으로 수리
        if (repaired.contains("{{") || repaired.contains("}}")) {
            // 모든 이중 중괄호를 단일 중괄호로 교체
            repaired = repaired.replaceAll("\\{\\{", "{");
            repaired = repaired.replaceAll("\\}\\}", "}");
        }

        // 시작과 끝이 없는 경우 추가
        if (!repaired.startsWith("{") && !repaired.startsWith("[")) {
            repaired = "{" + repaired;
        }

        if (!repaired.endsWith("}") && !repaired.endsWith("]")) {
            repaired = repaired + "}";
        }

        return repaired;
    }

    private String preprocessResponse(String response) {
        // 1. 앞뒤 공백 제거
        String cleaned = response.trim();

        // 2. 코드 블록 마커 제거
        cleaned = removeCodeBlocks(cleaned);

        // 3. JSON 객체 추출 (중괄호 두 개 이상 감싸진 경우 처리)
        cleaned = extractValidJson(cleaned);

        // 4. Python 리터럴을 JSON으로 변환
        cleaned = cleaned.replace("None", "null")
                .replace("True", "true")
                .replace("False", "false");

        // 5. 작은따옴표를 큰따옴표로 변환 (JSON 표준)
        cleaned = convertSingleQuotesToDouble(cleaned);

        // 6. 후행 쉼표 제거
        cleaned = removeTrailingCommas(cleaned);

        return cleaned;
    }

    private String removeCodeBlocks(String input) {
        // 다양한 코드 블록 패턴 제거
        String[] patterns = {
                "```json\\s*",
                "```\\s*",
                "`{3,}.*?`{3,}",
                "^```.*\n",
                "\n```.*$"
        };

        String result = input;
        for (String pattern : patterns) {
            result = result.replaceAll(pattern, "");
        }

        return result.trim();
    }

    private String extractValidJson(String input) {
        String trimmed = input.trim();

        // 1. 이중 중괄호로 감싸진 경우 처리 ({{...}}) - 수정된 부분
        if (trimmed.startsWith("{{") && trimmed.endsWith("}}")) {
            // 더 안전한 방법으로 이중 중괄호 처리
            String inner = trimmed.substring(2, trimmed.length() - 2).trim();

            // 중괄호 개수 확인하여 올바른 JSON 구조인지 검증
            if (isValidJsonStructure(inner)) {
                log.debug("Extracted from double braces: {}", inner);
                return inner;
            } else {
                // 이중 중괄호가 실제로는 단일 JSON 객체를 의미하는 경우
                String singleBrace = "{" + inner + "}";
                log.debug("Converted double braces to single: {}", singleBrace);
                return singleBrace;
            }
        }

        // 2. 일반적인 JSON 객체
        if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
            return trimmed;
        }

        // 3. 문자열 중간에 JSON이 있는 경우 추출
        Pattern jsonPattern = Pattern.compile("\\{[^{}]*(?:\\{[^{}]*\\}[^{}]*)*\\}", Pattern.DOTALL);
        Matcher matcher = jsonPattern.matcher(trimmed);

        if (matcher.find()) {
            String found = matcher.group();
            log.debug("Extracted JSON from text: {}", found);
            return found;
        }

        return trimmed;
    }

    /**
     * JSON 구조가 올바른지 검증하는 메서드
     */
    private boolean isValidJsonStructure(String json) {
        if (json == null || json.trim().isEmpty()) {
            return false;
        }

        String trimmed = json.trim();

        // 기본적인 JSON 구조 확인
        if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
            return true;
        }

        if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
            return true;
        }

        return false;
    }

    private String convertSingleQuotesToDouble(String input) {
        StringBuilder result = new StringBuilder();
        boolean inString = false;
        boolean inDoubleQuote = false;
        boolean escaped = false;

        for (int i = 0; i < input.length(); i++) {
            char c = input.charAt(i);

            if (escaped) {
                result.append(c);
                escaped = false;
                continue;
            }

            if (c == '\\') {
                result.append(c);
                escaped = true;
                continue;
            }

            if (c == '"' && !inString) {
                inDoubleQuote = !inDoubleQuote;
                result.append(c);
            } else if (c == '\'' && !inDoubleQuote) {
                if (inString) {
                    // 문자열 끝
                    result.append('"');
                    inString = false;
                } else {
                    // 문자열 시작인지 확인
                    if (isStringStart(input, i)) {
                        result.append('"');
                        inString = true;
                    } else {
                        result.append(c);
                    }
                }
            } else {
                result.append(c);
            }
        }

        return result.toString();
    }

    private boolean isStringStart(String input, int index) {
        // 이전 문자 확인 (키 또는 배열 시작)
        boolean validPrefix = false;
        for (int i = index - 1; i >= 0; i--) {
            char c = input.charAt(i);
            if (Character.isWhitespace(c)) continue;
            if (c == ':' || c == '[' || c == ',' || c == '{') {
                validPrefix = true;
            }
            break;
        }

        if (!validPrefix) return false;

        // 다음 문자들을 확인해서 문자열 시작인지 판단
        boolean foundClosing = false;
        for (int i = index + 1; i < input.length(); i++) {
            char c = input.charAt(i);
            if (c == '\'') {
                foundClosing = true;
                break;
            }
            // 다른 구문 요소를 만나면 문자열이 아님
            if (c == '{' || c == '}' || c == '[' || c == ']') {
                break;
            }
        }

        return foundClosing;
    }

    /**
     * JSON에서 후행 쉼표를 제거하는 메서드
     * 배열과 객체에서 마지막 요소 뒤의 쉼표를 제거
     */
    private String removeTrailingCommas(String input) {
        // 정규식을 사용해서 후행 쉼표 제거
        // 1. 배열에서 후행 쉼표 제거: ,\s*] -> ]
        String result = input.replaceAll(",\\s*]", "]");

        // 2. 객체에서 후행 쉼표 제거: ,\s*} -> }
        result = result.replaceAll(",\\s*}", "}");

        return result;
    }
}
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

        // 3. JSON 객체 추출 (수정된 로직)
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

    /**
     * 수정된 JSON 추출 로직
     */
    private String extractValidJson(String input) {
        String trimmed = input.trim();

        // 1. 이중 중괄호 패턴 처리 (템플릿 문법 등)
        if (trimmed.startsWith("{{") && trimmed.endsWith("}}")) {
            log.debug("Found double braces pattern, attempting to extract inner JSON");

            // 첫 번째 시도: 가장 바깥쪽 이중 중괄호를 단일 중괄호로 변경
            String withSingleBraces = "{" + trimmed.substring(2, trimmed.length() - 2) + "}";

            // 변경된 문자열이 유효한 JSON인지 확인
            if (isValidJsonStructure(withSingleBraces)) {
                log.debug("Successfully converted double braces to single: {}", withSingleBraces);
                return withSingleBraces;
            }

            log.warn("Failed to parse after converting double braces, trying to extract complete JSON structure");

            // 두 번째 시도: 완전한 JSON 구조 추출
            String extracted = extractLargestJsonObject(trimmed);
            if (extracted != null) {
                return extracted;
            }

            // 세 번째 시도: 이중 중괄호 내부의 완전한 구조 찾기
            String inner = trimmed.substring(2, trimmed.length() - 2).trim();
            extracted = extractLargestJsonObject(inner);
            if (extracted != null) {
                return extracted;
            }
        }

        // 2. 일반적인 JSON 객체
        if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
            return trimmed;
        }

        // 3. 배열 형태
        if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
            return trimmed;
        }

        // 4. 문자열 중간에 JSON이 있는 경우 추출
        return extractJsonWithRegex(trimmed);
    }

    /**
     * 정규식을 사용한 JSON 추출 - 중첩된 구조 지원
     */
    private String extractJsonWithRegex(String input) {
        // 가장 큰(완전한) JSON 객체를 찾기 위해 개선된 정규식 사용
        String found = extractLargestJsonObject(input);
        if (found != null) {
            log.debug("Extracted complete JSON object: {}", found);
            return found;
        }

        // 대괄호 균형을 맞춘 JSON 배열 찾기
        Pattern jsonArrayPattern = Pattern.compile("\\[(?:[^\\[\\]]|\\[[^\\[\\]]*\\])*\\]", Pattern.DOTALL);
        Matcher matcher = jsonArrayPattern.matcher(input);

        if (matcher.find()) {
            found = matcher.group();
            log.debug("Extracted JSON array with regex: {}", found);
            return found;
        }

        log.warn("Could not extract valid JSON from input: {}", input);
        return input;
    }

    /**
     * 중첩된 구조를 포함한 가장 큰 JSON 객체 추출
     */
    private String extractLargestJsonObject(String input) {
        int firstBrace = input.indexOf('{');
        if (firstBrace == -1) {
            return null;
        }

        int braceCount = 0;
        int start = firstBrace;
        int end = -1;

        for (int i = firstBrace; i < input.length(); i++) {
            char c = input.charAt(i);

            if (c == '{') {
                braceCount++;
            } else if (c == '}') {
                braceCount--;
                if (braceCount == 0) {
                    end = i;
                    break;
                }
            }
        }

        if (end != -1) {
            String extracted = input.substring(start, end + 1);

            // 추출된 JSON이 유효한지 검증
            if (isValidJsonStructure(extracted)) {
                return extracted;
            }
        }

        return null;
    }

    /**
     * JSON 구조가 올바른지 검증하는 메서드
     */
    private boolean isValidJsonStructure(String json) {
        if (json == null || json.trim().isEmpty()) {
            return false;
        }

        try {
            objectMapper.readTree(json.trim());
            return true;
        } catch (Exception e) {
            return false;
        }
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
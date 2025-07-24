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

        // 4. 이중 중괄호 처리 (전역 변환)
        cleaned = processDoubleBraces(cleaned);

        // 5. Python 리터럴을 JSON으로 변환
        cleaned = cleaned.replace("None", "null")
                .replace("True", "true")
                .replace("False", "false");

        // 6. 작은따옴표를 큰따옴표로 변환 (JSON 표준)
        cleaned = convertSingleQuotesToDouble(cleaned);

        // 7. 후행 쉼표 제거
        cleaned = removeTrailingCommas(cleaned);

        return cleaned;
    }

    /**
     * 이중 중괄호를 단일 중괄호로 변환
     */
    private String processDoubleBraces(String input) {
        // 이중 중괄호가 있는 경우 전역 변환
        if (input.contains("{{") || input.contains("}}")) {
            log.debug("Processing double braces in: {}", input);
            String result = input.replace("{{", "{").replace("}}", "}");
            log.debug("After double brace conversion: {}", result);
            return result;
        }
        return input;
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

        // 1. 이미 올바른 JSON 형태인 경우
        if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
            return trimmed;
        }
        if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
            return trimmed;
        }

        // 2. 텍스트 중에서 JSON 부분 추출
        String extracted = extractJsonFromText(trimmed);
        if (extracted != null) {
            return extracted;
        }

        // 3. 추출 실패 시 원본 반환
        log.warn("Could not extract JSON from input, returning original: {}", trimmed);
        return trimmed;
    }

    /**
     * 텍스트에서 JSON 부분을 추출 (이중 중괄호 패턴 포함)
     */
    private String extractJsonFromText(String input) {
        // 이중 중괄호 패턴 찾기
        int doubleBraceStart = input.indexOf("{{");
        if (doubleBraceStart != -1) {
            log.debug("Found double brace pattern at position: {}", doubleBraceStart);
            return extractBalancedJson(input, doubleBraceStart, "{{", "}}");
        }

        // 일반 중괄호 패턴 찾기
        int singleBraceStart = input.indexOf("{");
        if (singleBraceStart != -1) {
            log.debug("Found single brace pattern at position: {}", singleBraceStart);
            return extractBalancedJson(input, singleBraceStart, "{", "}");
        }

        // 배열 패턴 찾기
        int arrayStart = input.indexOf("[");
        if (arrayStart != -1) {
            log.debug("Found array pattern at position: {}", arrayStart);
            return extractBalancedJson(input, arrayStart, "[", "]");
        }

        return null;
    }

    /**
     * 균형잡힌 브레이스/브래킷으로 JSON 추출
     */
    private String extractBalancedJson(String input, int startPos, String openToken, String closeToken) {
        int openCount = 0;
        int currentPos = startPos;

        while (currentPos < input.length()) {
            if (input.startsWith(openToken, currentPos)) {
                openCount++;
                currentPos += openToken.length();
            } else if (input.startsWith(closeToken, currentPos)) {
                openCount--;
                currentPos += closeToken.length();

                if (openCount == 0) {
                    String extracted = input.substring(startPos, currentPos);
                    log.debug("Extracted balanced JSON: {}", extracted);
                    return extracted;
                }
            } else {
                currentPos++;
            }
        }

        log.warn("Could not find balanced closing token for: {}", openToken);
        return null;
    }

    /**
     * 정규식을 사용한 JSON 추출 - 중첩된 구조 지원 (폴백용)
     */
    private String extractJsonWithRegex(String input) {
        // 가장 큰(완전한) JSON 객체를 찾기 위해 개선된 정규식 사용
        String found = extractLargestJsonObject(input);
        if (found != null) {
            log.debug("Extracted complete JSON object: {}", found);
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
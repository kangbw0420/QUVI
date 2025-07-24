package com.daquv.agent.workflow.semanticquery.utils;

import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;

@Component
@Slf4j
public class FileUtils {

    /**
     * resources 폴더 기준으로 파일을 읽어서 문자열로 반환
     * @param path resources 폴더 내 파일 경로
     * @return 파일 내용
     */
    public String loadFile(String path) {
        StringBuilder content = new StringBuilder();

        try {
            ClassPathResource resource = new ClassPathResource(path);

            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8))) {

                String line;
                while ((line = reader.readLine()) != null) {
                    content.append(line).append("\n");
                }

                // 마지막 개행 문자 제거
                if (content.length() > 0) {
                    content.setLength(content.length() - 1);
                }

                return content.toString();
            }

        } catch (IOException e) {
            log.error("Failed to load file from resources: {}", path, e);
            throw new RuntimeException("Failed to load file from resources: " + path, e);
        }
    }
}
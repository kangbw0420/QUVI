package com.daquv.agent.workflow.semanticquery.utils;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.Map;

@Component
@Slf4j
public class YamlUtils {

    private final ObjectMapper yamlMapper;

    public YamlUtils() {
        this.yamlMapper = new ObjectMapper(new YAMLFactory());
    }

    /**
     * resources 폴더 기준으로 YAML 파일을 읽어서 Map으로 반환
     * @param path resources 폴더 내 YAML 파일 경로
     * @return 파싱된 YAML 데이터
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> loadYaml(String path) {
        try {
            ClassPathResource resource = new ClassPathResource(path);
            return yamlMapper.readValue(resource.getInputStream(), Map.class);
        } catch (IOException e) {
            log.error("Failed to load YAML file from resources: {}", path, e);
            throw new RuntimeException("Failed to load YAML from resources: " + path, e);
        }
    }
}
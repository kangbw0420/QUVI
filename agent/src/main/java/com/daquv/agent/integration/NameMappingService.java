package com.daquv.agent.integration;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import org.springframework.cache.annotation.Cacheable;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
public class NameMappingService {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Cacheable("stockMappings")
    public Map<String, String> getStockMappings() {
        return loadNameMappings("stock");
    }

    @Cacheable("bankMappings")
    public Map<String, String> getBankMappings() {
        return loadNameMappings("bank");
    }

    private Map<String, String> loadNameMappings(String nameType) {
        Map<String, String> mappings = new HashMap<>();

        String columnName = nameType + "_nm";
        String tableName = nameType + "name";
        String nickColumn = nameType + "_nick_nm";

        String query = String.format(
                "SELECT %s, %s FROM %s",
                nickColumn, columnName, tableName
        );

        try {
            List<Map<String, Object>> result = jdbcTemplate.queryForList(query);

            for (Map<String, Object> row : result) {
                String nickName = (String) row.get(nickColumn);
                String fullName = (String) row.get(columnName);
                if (nickName != null && fullName != null) {
                    mappings.put(nickName, fullName);
                }
            }

        } catch (Exception e) {
            System.err.println("Error loading " + nameType + " mappings: " + e.getMessage());
        }

        return mappings;
    }
}

package com.daquv.agent.workflow.semanticquery;

public enum SemanticEntity {
    ACCT("acct"),
    BAL("bal"),
    BAL_FORE("bal_fore"),
    TRSC("trsc"),
    TRSC_FORE("trsc_fore");

    private final String value;

    SemanticEntity(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static String[] getValues() {
        SemanticEntity[] entities = values();
        String[] result = new String[entities.length];
        for (int i = 0; i < entities.length; i++) {
            result[i] = entities[i].getValue();
        }
        return result;
    }

    @Override
    public String toString() {
        return value;
    }
}
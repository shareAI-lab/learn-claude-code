package com.agent;

import java.nio.file.Path;

/**
 * Configuration for the agent.
 */
public class AgentConfig {

    private final Path workdir;
    private final Path skillsDir;
    private final String apiKey;
    private final String baseUrl;
    private final String model;

    public AgentConfig() {
        this.workdir = Path.of(System.getProperty("user.dir"));
        this.skillsDir = this.workdir.resolve("skills");
        this.apiKey = System.getenv("ANTHROPIC_API_KEY");
        this.baseUrl = System.getenv("ANTHROPIC_BASE_URL");
        this.model = System.getenv().getOrDefault("MODEL_ID", "claude-sonnet-4-5-20250929");
    }

    public Path getWorkdir() {
        return workdir;
    }

    public Path getSkillsDir() {
        return skillsDir;
    }

    public String getApiKey() {
        return apiKey;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public String getModel() {
        return model;
    }

    public void validate() {
        if (apiKey == null || apiKey.isEmpty()) {
            throw new IllegalStateException("ANTHROPIC_API_KEY not set in .env file");
        }
    }
}

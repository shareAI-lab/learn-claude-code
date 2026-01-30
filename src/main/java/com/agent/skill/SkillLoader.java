package com.agent.skill;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Loads and manages skills from SKILL.md files.
 *
 * Progressive Disclosure:
 *   Layer 1: Metadata (name + description) - always loaded
 *   Layer 2: SKILL.md body - loaded on-demand
 *   Layer 3: Resources - hinted but not loaded
 */
public class SkillLoader {

    private final Path skillsDir;
    private final Map<String, Skill> skills = new HashMap<>();

    public SkillLoader(Path skillsDir) {
        this.skillsDir = skillsDir;
        loadSkills();
    }

    /**
     * Scan skills directory and load all valid SKILL.md files.
     * Only metadata is loaded at startup.
     */
    private void loadSkills() {
        if (!Files.exists(skillsDir)) {
            return;
        }

        try (var entries = Files.list(skillsDir)) {
            List<Path> skillDirs = entries
                    .filter(Files::isDirectory)
                    .collect(Collectors.toList());

            for (Path skillDir : skillDirs) {
                Path skillMd = skillDir.resolve("SKILL.md");
                if (Files.exists(skillMd)) {
                    try {
                        Skill skill = Skill.parse(skillMd);
                        skills.put(skill.getName(), skill);
                    } catch (Exception e) {
                        System.err.println("Failed to load skill from " + skillMd + ": " + e.getMessage());
                    }
                }
            }
        } catch (IOException e) {
            System.err.println("Failed to read skills directory: " + e.getMessage());
        }
    }

    /**
     * Get skill descriptions for system prompt (Layer 1).
     */
    public String getDescriptions() {
        if (skills.isEmpty()) {
            return "(no skills available)";
        }

        return skills.values().stream()
                .map(Skill::toString)
                .collect(Collectors.joining("\n"));
    }

    /**
     * Get full skill content for injection (Layer 2 + 3 hints).
     */
    public String getSkillContent(String name) {
        Skill skill = skills.get(name);
        if (skill == null) {
            return null;
        }
        return skill.getFullContent();
    }

    /**
     * List all available skill names.
     */
    public List<String> listSkills() {
        return skills.keySet().stream().sorted().collect(Collectors.toList());
    }

    /**
     * Check if a skill exists.
     */
    public boolean hasSkill(String name) {
        return skills.containsKey(name);
    }

    public int getSkillCount() {
        return skills.size();
    }
}

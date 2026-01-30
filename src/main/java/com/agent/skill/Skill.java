package com.agent.skill;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Represents a skill loaded from SKILL.md file.
 *
 * Format:
 * ---
 * name: pdf
 * description: Process PDF files...
 * ---
 * # Skill Content
 *
 * Detailed instructions...
 */
public class Skill {

    private static final Pattern FRONTMATTER_PATTERN =
            Pattern.compile("^---\\s*\n(.*?)\\n---\\s*\n(.*)$", Pattern.DOTALL);

    private final String name;
    private final String description;
    private final String body;
    private final Path path;
    private final Path dir;

    private Skill(String name, String description, String body, Path path, Path dir) {
        this.name = name;
        this.description = description;
        this.body = body;
        this.path = path;
        this.dir = dir;
    }

    /**
     * Parse a SKILL.md file.
     */
    public static Skill parse(Path skillMdPath) throws IOException {
        String content = Files.readString(skillMdPath.toPath());

        Matcher matcher = FRONTMATTER_PATTERN.matcher(content);
        if (!matcher.find()) {
            throw new IllegalArgumentException("Invalid SKILL.md format: missing frontmatter");
        }

        String frontmatter = matcher.group(1);
        String body = matcher.group(2).trim();

        Map<String, String> metadata = parseFrontmatter(frontmatter);

        String name = metadata.get("name");
        String description = metadata.get("description");

        if (name == null || description == null) {
            throw new IllegalArgumentException("SKILL.md must have name and description");
        }

        return new Skill(name, description, body, skillMdPath, skillMdPath.getParent());
    }

    private static Map<String, String> parseFrontmatter(String frontmatter) {
        Map<String, String> metadata = new HashMap<>();
        String[] lines = frontmatter.strip().split("\n");

        for (String line : lines) {
            if (line.contains(":")) {
                int colonIndex = line.indexOf(":");
                String key = line.substring(0, colonIndex).trim();
                String value = line.substring(colonIndex + 1).trim().replaceAll("[\"']", "");
                metadata.put(key, value);
            }
        }
        return metadata;
    }

    public String getName() {
        return name;
    }

    public String getDescription() {
        return description;
    }

    public String getBody() {
        return body;
    }

    public Path getPath() {
        return path;
    }

    public Path getDir() {
        return dir;
    }

    /**
     * Get resource hints (available subdirectories).
     */
    public Map<String, String> getResourceHints() {
        Map<String, String> hints = new HashMap<>();

        for (String folder : new String[]{"scripts", "references", "assets"}) {
            Path folderPath = dir.resolve(folder);
            if (Files.exists(folderPath)) {
                try {
                    var files = Files.list(folderPath)
                            .map(p -> p.getFileName().toString())
                            .toList();
                    if (!files.isEmpty()) {
                        hints.put(folder, String.join(", ", files));
                    }
                } catch (IOException e) {
                    // Ignore
                }
            }
        }
        return hints;
    }

    /**
     * Generate full skill content for injection.
     */
    public String getFullContent() {
        StringBuilder sb = new StringBuilder();
        sb.append("# Skill: ").append(name).append("\n\n");
        sb.append(body).append("\n");

        Map<String, String> hints = getResourceHints();
        if (!hints.isEmpty()) {
            sb.append("\n**Available resources in ").append(dir).append(":**\n");
            hints.forEach((folder, files) ->
                    sb.append("- ").append(folder).append(": ").append(files).append("\n")
            );
        }
        return sb.toString();
    }

    @Override
    public String toString() {
        return String.format("- %s: %s", name, description);
    }
}

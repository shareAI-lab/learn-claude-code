package com.agent.tool;

import com.agent.config.AgentConfig;
import com.agent.skill.SkillLoader;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Executes tool calls.
 */
public class ToolExecutor {

    private final AgentConfig config;
    private final SkillLoader skillLoader;
    private final Path workdir;

    public ToolExecutor(AgentConfig config, SkillLoader skillLoader) {
        this.config = config;
        this.skillLoader = skillLoader;
        this.workdir = config.getWorkdir();
    }

    public String execute(String name, Map<String, Object> args) {
        return switch (name) {
            case "bash" -> runBash((String) args.get("command"));
            case "read_file" -> runRead((String) args.get("path"), (Integer) args.getOrDefault("limit", null));
            case "write_file" -> runWrite((String) args.get("path"), (String) args.get("content"));
            case "edit_file" -> runEdit((String) args.get("path"), (String) args.get("old_text"), (String) args.get("new_text"));
            case "TodoWrite" -> runTodo((List<?>) args.get("items"));
            case "Task" -> runTask((String) args.get("description"), (String) args.get("prompt"), (String) args.get("agent_type"));
            case "Skill" -> runSkill((String) args.get("skill"));
            default -> "Unknown tool: " + name;
        };
    }

    private String runBash(String command) {
        if (containsDangerous(command)) {
            return "Error: Dangerous command blocked";
        }

        try {
            ProcessBuilder pb = new ProcessBuilder("bash", "-c", command);
            pb.directory(workdir.toFile());
            pb.redirectErrorStream(true);

            Process process = pb.start();

            // Read output with timeout
            StringBuilder output = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                String line;
                long start = System.currentTimeMillis();
                while (System.currentTimeMillis() - start < 60000) {
                    if (reader.ready()) {
                        line = reader.readLine();
                        if (line == null) break;
                        output.append(line).append("\n");
                    } else if (!process.isAlive()) {
                        break;
                    } else {
                        Thread.sleep(50);
                    }
                }
            }

            // Kill if still running
            if (process.isAlive()) {
                process.destroyForcibly();
                return output + "(timeout, process killed)";
            }

            String result = output.toString().trim();
            if (result.isEmpty()) {
                return "(no output)";
            }
            return result.length() > 50000 ? result.substring(0, 50000) + "\n...(truncated)" : result;

        } catch (Exception e) {
            return "Error: " + e.getMessage();
        }
    }

    private boolean containsDangerous(String command) {
        String lower = command.toLowerCase();
        return lower.contains("rm -rf /") ||
               lower.contains("sudo") ||
               lower.contains("shutdown") ||
               lower.contains("mkfs");
    }

    private String runRead(String pathStr, Integer limit) {
        try {
            Path path = safePath(pathStr);
            List<String> lines = Files.readAllLines(path);
            if (limit != null && limit > 0) {
                lines = lines.subList(0, Math.min(limit, lines.size()));
            }
            return String.join("\n", lines);
        } catch (Exception e) {
            return "Error: " + e.getMessage();
        }
    }

    private String runWrite(String pathStr, String content) {
        try {
            Path path = safePath(pathStr);
            Files.createDirectories(path.getParent());
            Files.writeString(path, content);
            return "Wrote " + content.length() + " bytes to " + pathStr;
        } catch (Exception e) {
            return "Error: " + e.getMessage();
        }
    }

    private String runEdit(String pathStr, String oldText, String newText) {
        try {
            Path path = safePath(pathStr);
            String content = Files.readString(path);
            if (!content.contains(oldText)) {
                return "Error: Text not found in " + pathStr;
            }
            String newContent = content.replace(oldText, newText, 1);
            Files.writeString(path, newContent);
            return "Edited " + pathStr;
        } catch (Exception e) {
            return "Error: " + e.getMessage();
        }
    }

    private String runTodo(List<?> items) {
        // Simplified - just validate
        int index = 0;
        for (Object item : items) {
            if (!(item instanceof Map<?, ?> m)) {
                return "Error: Invalid item format at index " + index;
            }
            if (!m.containsKey("content") || !m.containsKey("activeForm")) {
                return "Error: Item " + index + " missing content or activeForm";
            }
            String status = (String) m.getOrDefault("status", "pending");
            if (!status.equals("pending") && !status.equals("in_progress") && !status.equals("completed")) {
                return "Error: Invalid status at index " + index;
            }
            index++;
        }
        return "Todo updated with " + items.size() + " items";
    }

    private String runTask(String description, String prompt, String agentType) {
        // Subagent execution - simplified placeholder
        return "[Task executed: " + description + " with agent type: " + agentType + "]";
    }

    private String runSkill(String skillName) {
        String content = skillLoader.getSkillContent(skillName);

        if (content == null) {
            String available = String.join(", ", skillLoader.listSkills());
            return "Error: Unknown skill '" + skillName + "'. Available: " + (available.isEmpty() ? "none" : available);
        }

        return String.format("""
                <skill-loaded name="%s">
                %s
                </skill-loaded>

                Follow the instructions in the skill above to complete the user's task.""", skillName, content);
    }

    private Path safePath(String pathStr) {
        Path path = workdir.resolve(pathStr).normalize();
        if (!path.startsWith(workdir)) {
            throw new IllegalArgumentException("Path escapes workspace: " + pathStr);
        }
        return path;
    }
}

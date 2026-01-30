package com.agent.tool;

import com.agent.config.AgentConfig;
import com.agent.skill.SkillLoader;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Tool definitions for the agent.
 */
public class ToolDefinitions {

    public static final List<Map<String, Object>> BASE_TOOLS = createBaseTools();
    public static final Map<String, Object> TASK_TOOL = createTaskTool();
    public static final Map<String, Object> SKILL_TOOL = createSkillTool(SkillLoader.class.getSimpleName());

    private static List<Map<String, Object>> createBaseTools() {
        List<Map<String, Object>> tools = new ArrayList<>();

        // bash tool
        Map<String, Object> bash = new HashMap<>();
        bash.put("name", "bash");
        bash.put("description", "Run shell command.");
        Map<String, Object> bashInput = new HashMap<>();
        bashInput.put("type", "object");
        Map<String, Object> bashProps = new HashMap<>();
        bashProps.put("command", Map.of("type", "string"));
        bashInput.put("properties", bashProps);
        bashInput.put("required", List.of("command"));
        bash.put("input_schema", bashInput);
        tools.add(bash);

        // read_file tool
        Map<String, Object> read = new HashMap<>();
        read.put("name", "read_file");
        read.put("description", "Read file contents.");
        Map<String, Object> readInput = new HashMap<>();
        readInput.put("type", "object");
        Map<String, Object> readProps = new HashMap<>();
        readProps.put("path", Map.of("type", "string"));
        readProps.put("limit", Map.of("type", "integer"));
        readInput.put("properties", readProps);
        readInput.put("required", List.of("path"));
        read.put("input_schema", readInput);
        tools.add(read);

        // write_file tool
        Map<String, Object> write = new HashMap<>();
        write.put("name", "write_file");
        write.put("description", "Write content to file.");
        Map<String, Object> writeInput = new HashMap<>();
        writeInput.put("type", "object");
        Map<String, Object> writeProps = new HashMap<>();
        writeProps.put("path", Map.of("type", "string"));
        writeProps.put("content", Map.of("type", "string"));
        writeInput.put("properties", writeProps);
        writeInput.put("required", List.of("path", "content"));
        write.put("input_schema", writeInput);
        tools.add(write);

        // edit_file tool
        Map<String, Object> edit = new HashMap<>();
        edit.put("name", "edit_file");
        edit.put("description", "Replace exact text in file.");
        Map<String, Object> editInput = new HashMap<>();
        editInput.put("type", "object");
        Map<String, Object> editProps = new HashMap<>();
        editProps.put("path", Map.of("type", "string"));
        editProps.put("old_text", Map.of("type", "string"));
        editProps.put("new_text", Map.of("type", "string"));
        editInput.put("properties", editProps);
        editInput.put("required", List.of("path", "old_text", "new_text"));
        edit.put("input_schema", editInput);
        tools.add(edit);

        // TodoWrite tool
        Map<String, Object> todo = new HashMap<>();
        todo.put("name", "TodoWrite");
        todo.put("description", "Update task list.");
        Map<String, Object> todoInput = new HashMap<>();
        todoInput.put("type", "object");
        Map<String, Object> todoProps = new HashMap<>();
        Map<String, Object> itemsSchema = new HashMap<>();
        itemsSchema.put("type", "array");
        Map<String, Object> itemSchema = new HashMap<>();
        itemSchema.put("type", "object");
        Map<String, Object> itemProps = new HashMap<>();
        itemProps.put("content", Map.of("type", "string"));
        itemProps.put("status", Map.of("type", "string", "enum", List.of("pending", "in_progress", "completed")));
        itemProps.put("activeForm", Map.of("type", "string"));
        itemSchema.put("properties", itemProps);
        itemSchema.put("required", List.of("content", "status", "activeForm"));
        itemsSchema.put("items", itemSchema);
        todoProps.put("items", itemsSchema);
        todoInput.put("properties", todoProps);
        todoInput.put("required", List.of("items"));
        todo.put("input_schema", todoInput);
        tools.add(todo);

        return tools;
    }

    private static Map<String, Object> createTaskTool() {
        Map<String, Object> task = new HashMap<>();
        task.put("name", "Task");
        task.put("description", "Spawn a subagent for a focused subtask.");
        Map<String, Object> taskInput = new HashMap<>();
        taskInput.put("type", "object");
        Map<String, Object> taskProps = new HashMap<>();
        taskProps.put("description", Map.of("type", "string", "description", "Short task description"));
        taskProps.put("prompt", Map.of("type", "string", "description", "Detailed instructions"));
        taskProps.put("agent_type", Map.of("type", "string", "enum", List.of("explore", "code", "plan")));
        taskInput.put("properties", taskProps);
        taskInput.put("required", List.of("description", "prompt", "agent_type"));
        task.put("input_schema", taskInput);
        return task;
    }

    private static Map<String, Object> createSkillTool(String skillDescriptions) {
        Map<String, Object> skill = new HashMap<>();
        skill.put("name", "Skill");
        skill.put("description", "Load a skill to gain specialized knowledge.");
        Map<String, Object> skillInput = new HashMap<>();
        skillInput.put("type", "object");
        Map<String, Object> skillProps = new HashMap<>();
        skillProps.put("skill", Map.of("type", "string", "description", "Name of the skill to load"));
        skillInput.put("properties", skillProps);
        skillInput.put("required", List.of("skill"));
        skill.put("input_schema", skillInput);
        return skill;
    }

    public static List<Map<String, Object>> getAllTools(SkillLoader skillLoader) {
        List<Map<String, Object>> all = new ArrayList<>(BASE_TOOLS);
        all.add(TASK_TOOL);
        // Update SKILL_TOOL with current descriptions
        Map<String, Object> skillTool = new HashMap<>(SKILL_TOOL);
        skillTool.put("description", String.format(
                "Load a skill to gain specialized knowledge.\n\nAvailable skills:\n%s\n\nWhen to use: IMMEDIATELY when task matches a skill description.",
                skillLoader.getDescriptions()
        ));
        all.add(skillTool);
        return all;
    }
}

package com.agent;

import com.agent.config.AgentConfig;
import com.agent.skill.SkillLoader;
import com.agent.tool.ToolDefinitions;
import com.agent.tool.ToolExecutor;
import com.anthropic.Anthropic;
import com.anthropic.models.Message;
import com.anthropic.models.Tool;
import com.anthropic.models.ToolUseBlock;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Main agent loop.
 *
 * Pattern:
 *   while True:
 *       response = model(messages, tools)
 *       if response.stop_reason != "tool_use":
 *           return response.text
 *       results = execute(response.tool_calls)
 *       messages.append(results)
 */
public class Agent {

    private final Anthropic client;
    private final AgentConfig config;
    private final SkillLoader skillLoader;
    private final ToolExecutor toolExecutor;
    private final String systemPrompt;

    public Agent(AgentConfig config, SkillLoader skillLoader, ToolExecutor toolExecutor) {
        this.config = config;
        this.skillLoader = skillLoader;
        this.toolExecutor = toolExecutor;

        // Build client
        Anthropic.Builder builder = new Anthropic.Builder()
                .apiKey(config.getApiKey());

        if (config.getBaseUrl() != null) {
            builder.baseUrl(config.getBaseUrl());
        }

        this.client = builder.build();

        // Build system prompt
        this.systemPrompt = buildSystemPrompt();
    }

    private String buildSystemPrompt() {
        return String.format("""
                You are a coding agent at %s.

                Loop: plan -> act with tools -> report.

                **Skills available** (invoke with Skill tool when task matches):
                %s

                **Subagents available** (invoke with Task tool for focused subtasks):
                - explore: Read-only agent for exploring code
                - code: Full agent for implementing features
                - plan: Planning agent for design strategies

                Rules:
                - Use Skill tool IMMEDIATELY when a task matches a skill description
                - Use Task tool for subtasks needing focused exploration
                - Use TodoWrite to track multi-step work
                - Prefer tools over prose. Act, don't just explain.
                - After finishing, summarize what changed.""",
                config.getWorkdir(),
                skillLoader.getDescriptions()
        );
    }

    /**
     * Execute the agent loop with user messages.
     *
     * @param messages List of messages (will be modified)
     * @return Final response text
     */
    public String run(List<Map<String, Object>> messages) {
        List<Tool> tools = ToolDefinitions.getAllTools(skillLoader).stream()
                .map(this::toTool)
                .toList();

        while (true) {
            // Call model
            Message response = client.messages.create(msg -> {
                msg.model(config.getModel());
                msg.maxTokens(8000);
                msg.system(systemPrompt);
                msg.messages(messages);
                msg.tools(tools);
            });

            // Handle non-tool response
            if (!response.stopReason().equals("tool_use")) {
                messages.add(Map.of("role", "assistant", "content", response.content()));
                return extractText(response);
            }

            // Process tool calls
            List<ToolUseBlock> toolCalls = response.content().stream()
                    .filter(b -> b.type().equals("tool_use"))
                    .map(b -> (ToolUseBlock) b)
                    .toList();

            // Print assistant text
            response.content().stream()
                    .filter(b -> b.type().equals("text"))
                    .forEach(b -> System.out.println(((com.anthropic.models.TextBlock) b).text()));

            // Execute tools
            List<Map<String, Object>> results = new ArrayList<>();
            for (ToolUseBlock tc : toolCalls) {
                System.out.println("\n> " + tc.name());

                Map<String, Object> args = parseToolInput(tc.input());
                String output = toolExecutor.execute(tc.name(), args);
                String preview = output.length() > 200 ? output.substring(0, 200) + "..." : output;
                System.out.println("  " + preview);

                results.add(Map.of(
                        "type", "tool_result",
                        "tool_use_id", tc.id(),
                        "content", output
                ));
            }

            // Append to messages
            messages.add(Map.of("role", "assistant", "content", response.content()));
            messages.add(Map.of("role", "user", "content", results));
        }
    }

    private Tool toTool(Map<String, Object> toolDef) {
        return Tool.of(
                (String) toolDef.get("name"),
                (String) toolDef.get("description"),
                (Map) toolDef.get("input_schema")
        );
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseToolInput(Object input) {
        if (input instanceof Map) {
            return (Map<String, Object>) input;
        }
        return new HashMap<>();
    }

    private String extractText(Message response) {
        return response.content().stream()
                .filter(b -> b.type().equals("text"))
                .map(b -> ((com.anthropic.models.TextBlock) b).text())
                .reduce("", (a, b) -> a + b);
    }
}

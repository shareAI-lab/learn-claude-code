package com.agent;

import com.agent.config.AgentConfig;
import com.agent.skill.SkillLoader;
import com.agent.tool.ToolExecutor;
import com.agent.util.Environment;

/**
 * v4 Skills Agent - Java Implementation
 *
 * Core Philosophy: "Knowledge Externalization"
 *
 * Main loop pattern:
 *   while True:
 *       response = model(messages, tools)
 *       if response.stop_reason != "tool_use":
 *           return response.text
 *       results = execute(response.tool_calls)
 *       messages.append(results)
 */
public class AgentApplication {

    public static void main(String[] args) {
        // Load environment
        Environment.load();

        // Initialize components
        AgentConfig config = new AgentConfig();
        SkillLoader skillLoader = new SkillLoader(config.getSkillsDir());
        ToolExecutor toolExecutor = new ToolExecutor(config, skillLoader);

        // Start REPL
        AgentRepl repl = new AgentRepl(config, skillLoader, toolExecutor);
        repl.run();
    }
}

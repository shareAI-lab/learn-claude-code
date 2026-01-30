package com.agent;

import com.agent.config.AgentConfig;
import com.agent.skill.SkillLoader;
import com.agent.tool.ToolExecutor;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Scanner;

/**
 * Interactive REPL for the agent.
 */
public class AgentRepl {

    private final AgentConfig config;
    private final SkillLoader skillLoader;
    private final ToolExecutor toolExecutor;
    private final Scanner scanner;

    public AgentRepl(AgentConfig config, SkillLoader skillLoader, ToolExecutor toolExecutor) {
        this.config = config;
        this.skillLoader = skillLoader;
        this.toolExecutor = toolExecutor;
        this.scanner = new Scanner(System.in);
    }

    public void run() {
        System.out.printf("Mini Claude Code v4 (Java) - %s%n", config.getWorkdir());
        System.out.printf("Skills: %s%n", skillLoader.getSkillCount() > 0
                ? String.join(", ", skillLoader.listSkills()) : "none");
        System.out.println("Type 'exit' to quit.\n");

        List<Map<String, Object>> history = new ArrayList<>();

        while (true) {
            System.out.print("You: ");
            System.out.flush();

            String input;
            try {
                input = scanner.nextLine();
            } catch (Exception e) {
                break;
            }

            if (input == null || input.trim().isEmpty() || input.trim().toLowerCase().equals("exit")) {
                break;
            }

            history.add(Map.of("role", "user", "content", input.trim()));

            try {
                Agent agent = new Agent(config, skillLoader, toolExecutor);
                String response = agent.run(history);
                System.out.println("\n" + response);
            } catch (Exception e) {
                System.err.println("\nError: " + e.getMessage());
                e.printStackTrace();
            }

            System.out.println();
        }

        scanner.close();
    }
}

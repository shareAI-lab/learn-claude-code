package com.agent.util;

import io.github.cdimascio.dotenv.Dotenv;

/**
 * Environment loader for .env files.
 */
public class Environment {

    private static boolean loaded = false;

    public static void load() {
        if (loaded) {
            return;
        }

        try {
            Dotenv dotenv = Dotenv.configure()
                    .directory(System.getProperty("user.dir"))
                    .ignoreIfMissing()
                    .load();

            dotenv.entries().forEach(entry ->
                    System.setProperty(entry.getKey(), entry.getValue())
            );

            loaded = true;
        } catch (Exception e) {
            // Ignore if .env not found
        }
    }
}

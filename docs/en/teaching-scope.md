# Teaching Scope

This document explains what you will learn in this repo, what is deliberately left out, and how each chapter stays aligned with your mental model as it grows.

## The Goal Of This Repo

This is not a line-by-line commentary on some upstream production codebase.

The real goal is:

**teach you how to build a high-completion coding-agent harness from scratch.**

That implies three obligations:

1. you can actually rebuild it
2. you keep the mainline clear instead of drowning in side detail
3. you do not absorb mechanisms that do not really exist

## What Every Chapter Should Cover

Every mainline chapter should make these things explicit:

- what problem the mechanism solves
- which module or layer it belongs to
- what state it owns
- what data structures it introduces
- how it plugs back into the loop
- what changes in the runtime flow after it appears

If you finish a chapter and still cannot say where the mechanism lives or what state it owns, the chapter is not done yet.

## What We Deliberately Keep Simple

These topics are not forbidden, but they should not dominate your learning path:

- packaging, build, and release flow
- cross-platform compatibility glue
- telemetry and enterprise policy wiring
- historical compatibility branches
- product-specific naming accidents
- line-by-line upstream code matching

Those belong in appendices, maintainer notes, or later productization notes, not at the center of the beginner path.

## What "High Fidelity" Really Means Here

High fidelity in a teaching repo does not mean reproducing every edge detail 1:1.

It means staying close to the true system backbone:

- core runtime model
- module boundaries
- key records
- state transitions
- cooperation between major subsystems

In short:

**be highly faithful to the trunk, and deliberate about teaching simplifications at the edges.**

## Who This Is For

You do not need to be an expert in agent platforms.

A better assumption about you:

- basic Python is familiar
- functions, classes, lists, and dictionaries are familiar
- agent systems may be completely new

That means the chapters should:

- explain new concepts before using them
- keep one concept complete in one main place
- move from "what it is" to "why it exists" to "how to build it"

## Recommended Chapter Structure

Mainline chapters should roughly follow this order:

1. what problem appears without this mechanism
2. first explain the new terms
3. give the smallest useful mental model
4. show the core records / data structures
5. show the smallest correct implementation
6. show how it plugs into the main loop
7. show common beginner mistakes
8. show what a higher-completion version would add later

## Terminology Guideline

If a chapter introduces a term from these categories, it should explain it:

- design pattern
- data structure
- concurrency term
- protocol / networking term
- uncommon engineering vocabulary

Examples:

- state machine
- scheduler
- queue
- worktree
- DAG
- protocol envelope

Do not drop the name without the explanation.

## Minimal Correct Version Principle

Real mechanisms are often complex, but teaching works best when it does not start with every branch at once.

Prefer this sequence:

1. show the smallest correct version
2. explain what core problem it already solves
3. show what later iterations would add

Examples:

- permission system: first `deny -> mode -> allow -> ask`
- error recovery: first three major recovery branches
- task system: first task records, dependencies, and unlocks
- team protocols: first request / response plus `request_id`

## Checklist For Rewriting A Chapter

- Does the first screen explain why the mechanism exists?
- Are new terms explained before they are used?
- Is there a small mental model or flow picture?
- Are key records listed explicitly?
- Is the plug-in point back into the loop explained?
- Are core mechanisms separated from peripheral product detail?
- Are the easiest confusion points called out?
- Does the chapter avoid inventing mechanisms not supported by the repo?

## How To Use Reverse-Engineered Source Material

Reverse-engineered source should be used as:

**maintainer calibration material**

Use it to:

- verify the mainline mechanism is described correctly
- verify important boundaries and records are not missing
- verify the teaching implementation did not drift into fiction

It should never become a prerequisite for understanding the teaching docs.

## Key Takeaway

**The quality of a teaching repo is decided less by how many details it mentions and more by whether the important details are fully explained and the unimportant details are safely omitted.**

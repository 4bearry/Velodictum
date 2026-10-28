---
name: prompt-enhancer
description: >-
  Analyzes, refines, and optimizes user prompts for AI models and coding agents.
  Use when the user asks to improve, optimize, compress, refine, or review a prompt,
  reduce token usage, or prepare a high-performance prompt before executing a task.
---

# Prompt Enhancer & Token Optimizer

Expert skill for refining, sharpening, and compressing user prompts before sending them to AI models or coding agents (like Antigravity, Gemini, Claude, or GPT).

## Core Objectives

1. **Maximize Accuracy & Output Quality**: Provide unambiguous intent, clear constraints, explicit scope, and actionable acceptance criteria.
2. **Minimize Token Waste**: Eliminate pleasantries, filler phrases, vague rambling, and repetitive instructions to save input tokens and keep model reasoning focused.
3. **Ground in the Codebase**: Replace vague terms ("the audio engine", "that one file") with exact file paths (`file:///...`) and symbol names when working in an active repository.
4. **Surface Hidden Assumptions**: Catch missing edge cases, error handling expectations, and architectural boundaries before the model starts coding.

---

## The Optimization Workflow

When activated with a draft prompt or task description from the user:

### Step 1: Analyze the Draft Prompt
Evaluate the draft against the **5 Pillars of High-Performance Prompts**:
- **Goal / Task**: Is the ultimate objective clearly stated in 1–2 sentences?
- **Context & Targets**: Are the specific files, modules, or APIs explicitly named?
- **Constraints**: Are there restrictions on libraries, backwards compatibility, UI/UX, or patterns?
- **Ambiguities / Missing Info**: Are there missing specifications (e.g. error handling, data types, side effects)?
- **Token Density**: How much conversational boilerplate can be removed without losing information?

### Step 2: Codebase Grounding (If relevant)
If the prompt refers to the local project:
- Quickly identify the relevant files or configs using codebase tools.
- Include exact file links and function/class identifiers in the optimized prompt.

### Step 3: Clarify Underspecified Requirements (If needed)
If the user's intent is ambiguous or critical technical choices are unmentioned, use `ask_question` or concise bullet points to clarify before finalizing.

### Step 4: Construct the Optimized Prompt
Structure the prompt according to the **Universal Agentic Template**:

```markdown
### Objective
[Clear, single-sentence statement of what needs to be achieved]

### Context & Target Files
- Target: `[path/to/file.ext]` (specifically `[ClassName]` / `[function_name]`)
- Dependencies / Reference: `[path/to/reference.ext]`

### Requirements & Behavior
1. [Precise functional requirement]
2. [Edge case or data validation requirement]
3. [Expected integration / signature]

### Constraints
- [e.g. Do not break existing API signatures]
- [e.g. Preserve test suite compatibility, zero external dependencies]

### Verification
- [Command or unit test to prove correctness, e.g. `pytest tests/test_feature.py`]
```

*(Note: For simple or non-coding prompts, adapt the template to be appropriately lightweight.)*

---

## Output Format to the User

Always present the result clearly to the user:

1. **Optimized Prompt**: Placed in a standalone Markdown block so the user can easily copy it or tell the agent "Execute this now".
2. **What Changed & Why**:
   - **Token Reduction**: Estimated % reduction in token fluff.
   - **Key Clarifications**: What was made explicit (e.g. error handling, edge cases, target files).
3. **Quick Action Prompt**: Ask if they want to execute this optimized prompt immediately or adjust any details.

---

## Token Optimization Rules

- **Cut Conversational Preamble**: Remove phrases like "Can you please...", "I was wondering if you could help me write...", "Hey there, in this project I have...".
- **Use Imperative & Structured Language**: "Refactor X to do Y" instead of "I would like you to consider maybe refactoring X so that it does Y".
- **Avoid Negative Prompt Traps**: Instead of listing many things NOT to do in verbose prose, state the positive rule with concise boundaries.
- **Deduplicate Instructions**: Consolidate repeated mentions of guidelines or style rules into single bullet points.

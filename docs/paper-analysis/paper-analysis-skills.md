---
name: bmad-paper-analysis
description: 'Academic paper analyzer based on the Three-Pass Approach. Use when the user wants to quickly understand a paper, extract its 5Cs, analyze figures, or get focal points for deep reading.'
---

# BMad Paper Analysis Skill

**Goal:** Analyze uploaded academic papers or e-books using S. Keshav's "Three-Pass Approach" to provide the user with a quick overview, key content summary, and deep-dive focal points.

## Workflow Instructions

### 1. The First Pass (Bird's-eye view)
- Scan the title, abstract, introduction, section headings, and conclusions.
- Output the 5 Cs:
  - **Category**: Measurement? Analysis? Prototype?
  - **Context**: Related work and theoretical bases.
  - **Correctness**: Validity of assumptions.
  - **Contributions**: Main contributions of the paper.
  - **Clarity**: Writing quality.

### 2. The Second Pass (Content Grasp)
- Ignore deep proofs but focus on the main thrust and supporting evidence.
- Analyze figures, diagrams, and graphs. Check for proper labeling and statistical significance (error bars).
- Identify key unread references that are critical for background context.

### 3. The Third Pass (Virtual Re-implementation)
- Challenge every assumption in every statement.
- Identify hidden failings, implicit assumptions, and potential issues with experimental techniques.
- Provide the user with a targeted list of focal points for their own deep reading, including ideas for future work.

## Critical Rules
- **No Filler**: Only report real findings from the text.
- **Structured Output**: Follow the 3-Pass structure clearly. Do not mix First Pass findings with Third Pass critiques.
- **Empathetic Guide**: Your goal is to save the user time and point them exactly where they need to focus their mental energy.
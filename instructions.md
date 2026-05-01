# 🤖 AI Agent Instructions

Welcome to the **Vialactée** repository! 

If you are an AI assistant, an LLM, or an autonomous agent assigned to work on this project, **you must familiarize yourself with the custom architecture and strict rules of this codebase** before generating any code or proposing structural modifications. 

To prevent hallucinations, avoid unnecessary generic libraries, and maintain our highly optimized real-time DSP and hardware rendering engines, please redirect your attention to the following directories immediately:

## 1. Primary Context & Architecture (`/.agents/`)
**Start here.** The `.agents` directory contains the foundational context for the project, written specifically for AI consumption.
- Read **`.agents/AGENT.md`** for a high-level overview of the mathematical logic, the numpy-vectorized DSP engine, the directory structure, and the strict technical rules you must follow.
- Read **`.agents/PLAN.md`** to understand our ongoing development roadmap (e.g., the 5-second Audio Lookahead and ESP32 routing) so you know how current tasks fit into the bigger picture.

## 2. In-Depth Component Documentation (`/.agents/docs/`)
Once you understand the overarching architecture from `.agents`, consult the `.agents/docs/` folder for specific algorithm designs and spatial orchestration rules.
- Read **`.agents/docs/00_AGENT_NAVIGATION.md`** first. It serves as an index map for all the detailed documentation in the folder.
- Inside `.agents/docs/`, you will find comprehensive explanations on rhythm tracking (Phase Inertia Flywheels), structural music event detection (Asserved Envelopes), and spatial LED transition logic (The Transition Director).

> ⚠️ **CRITICAL INSTRUCTION:** Do not proceed with code modifications without first checking these directories to ensure your proposed logic correctly aligns with the non-causal mathematical frameworks and asynchronous constraints established for Vialactée.

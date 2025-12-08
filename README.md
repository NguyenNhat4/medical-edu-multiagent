<h1 align="center">Pocket Flow Project Template: Agentic Coding</h1>

<p align="center">
  <a href="https://github.com/The-Pocket/PocketFlow" target="_blank">
    <img 
      src="./assets/banner.png" width="800"
    />
  </a>
</p>

This is a project template for Agentic Coding with [Pocket Flow](https://github.com/The-Pocket/PocketFlow), a 100-line LLM framework, and your editor of choice.

- We have included rules files for various AI coding assistants to help you build LLM projects:
  - [.cursorrules](.cursorrules) for Cursor AI
  - [.clinerules](.clinerules) for Cline
  - [.windsurfrules](.windsurfrules) for Windsurf
  - [.goosehints](.goosehints) for Goose
  - Configuration in [.github](.github) for GitHub Copilot
  - [CLAUDE.md](CLAUDE.md) for Claude Code
  - [GEMINI.md](GEMINI.md) for Gemini
  
- Want to learn how to build LLM projects with Agentic Coding?

  - Check out the [Agentic Coding Guidance](https://the-pocket.github.io/PocketFlow/guide.html)
    
  - Check out the [YouTube Tutorial](https://www.youtube.com/@ZacharyLLM?sub_confirmation=1)

# Medical Training Multi-Agent System

A specialized agentic system for generating medical training materials (Lectures, Slides, Notes) using PocketFlow.

## Features
- **Structured Workflow**: Interview -> Plan -> Refine -> Generate.
- **Dynamic Artifacts**: Generates only the requested documents (e.g., just Slides or full package).
- **Parallel Generation**: Uses Batch Nodes to generate content concurrently.
- **Language**: Fully Vietnamese support.

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set API Key:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
3. Run the agent:
   ```bash
   python main.py
   ```

## Architecture
See `docs/design.md` for details.

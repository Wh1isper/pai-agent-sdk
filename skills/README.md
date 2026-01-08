# pai-agent-sdk

[![Release](https://img.shields.io/github/v/release/wh1isper/pai-agent-sdk)](https://img.shields.io/github/v/release/wh1isper/pai-agent-sdk)
[![Build status](https://img.shields.io/github/actions/workflow/status/wh1isper/pai-agent-sdk/main.yml?branch=main)](https://github.com/wh1isper/pai-agent-sdk/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/wh1isper/pai-agent-sdk/branch/main/graph/badge.svg)](https://codecov.io/gh/wh1isper/pai-agent-sdk)
[![Commit activity](https://img.shields.io/github/commit-activity/m/wh1isper/pai-agent-sdk)](https://img.shields.io/github/commit-activity/m/wh1isper/pai-agent-sdk)
[![License](https://img.shields.io/github/license/wh1isper/pai-agent-sdk)](https://img.shields.io/github/license/wh1isper/pai-agent-sdk)

Toolsets and context management for building agents with Pydantic AI.

## Installation

```bash
# Recommended: install with all optional dependencies
pip install pai-agent-sdk[all]
uv add pai-agent-sdk[all]

# Or install individual extras as needed
pip install pai-agent-sdk[docker]    # Docker sandbox support
pip install pai-agent-sdk[web]       # Web tools (tavily, firecrawl, markitdown)
pip install pai-agent-sdk[document]  # Document processing (pymupdf, markitdown)
```

## For Agent Users

If you're using an AI agent (e.g., Claude, Cursor) that supports skills, you can download the latest `SKILL.zip` from the [Releases](https://github.com/wh1isper/pai-agent-sdk/releases) page. The skill package is automatically built and uploaded during each release via GitHub Actions.

## Quick Start

Check out the [examples/](examples/) directory for ready-to-run examples:

- [hello_world.py](examples/hello_world.py) - Basic agent setup and usage
- [coding.py](examples/coding.py) - Coding assistant example
- [deepresearch.py](examples/deepresearch.py) - Deep research agent example

## Configuration

Copy `.env.example` to `.env` and configure your API keys. See [.env.example](.env.example) for all available environment variables.

## Documentation

- [AgentContext & Sessions](docs/context.md) - Session state, resumable sessions, extending context
- [Toolset Architecture](docs/toolset.md) - Create tools, use hooks, handle errors, extend Toolset
- [Custom Environments](docs/environment.md) - Extend context management with custom environments
- [Logging Configuration](docs/logging.md) - Configure SDK logging levels

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

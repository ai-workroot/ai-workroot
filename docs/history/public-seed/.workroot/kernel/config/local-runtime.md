# Local Runtime

AI Workroot is file-first, but real Workroots often need local machine-specific configuration.

Examples:

- local database credentials
- MCP server definitions
- private agent settings
- API keys or local environment files
- tool paths that differ by operating system

These files may exist locally, but they must not become durable knowledge or public project content.

## Default Local Secrets

The starter `.gitignore` excludes common local runtime files:

- `.env`
- `.env.*`
- `.my.cnf`
- `.mcp.json`
- `.codex/`
- `.claude/`
- `.workroot/runtime/local/mcp_servers.json`
- `.workroot/runtime/local/*_servers.json`

Projects may add more local ignore rules for their own tools.

## Rule

Secrets may be used locally to do real work, but they must not be copied into:

- `space/mind/`
- task notes
- reports
- public docs
- committed configuration
- examples

If a workflow needs shareable setup, create an example file with placeholders instead of real secrets.

## Agent Behavior

Before publishing, exporting, sharing, or committing a Workroot, agents should check whether local runtime files, generated databases, caches, or sensitive artifacts are present.

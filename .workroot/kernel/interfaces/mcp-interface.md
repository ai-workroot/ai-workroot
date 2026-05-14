# MCP Interface

MCP bridges are external capability transports.

An MCP integration must declare server identity, trust boundary, tool discovery, read scope, write scope, network behavior, secret behavior, durable write behavior, confirmation requirements, and failure behavior.

MCP servers must not silently write durable memory, bypass release rules, or read secrets without explicit user confirmation.

MCP details are loaded only when relevant to the active task.

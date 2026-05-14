# Tool Interface

Tools are executable or callable helpers used by agents, extensions, or user programs.

Tools must declare purpose, inputs, outputs, read scope, write scope, network behavior, secret behavior, destructive behavior, generated stores, and confirmation requirements when they are repeatable or non-trivial.

Tools must keep files as the durable source of truth unless they are explicitly declared as rebuildable accelerators.

Tool failure should be visible and recoverable. Tools should not silently corrupt registries, kernel contracts, or user-owned material.

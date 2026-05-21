# Workroot System Area

`.workroot/` contains the AI Workroot system area.

Ordinary users do not need to open or manage this folder during normal work.

It contains:

- `kernel/`: stable law, contracts, schemas, interfaces, agent rules, and validation expectations
- `extensions/`: replaceable capabilities, skills, MCP bridges, adapters, and drivers
- `runtime/`: rebuildable state, indexes, current context, internal work records, data stores, caches, and logs

Files in `space/` remain the durable user-owned source of truth. Runtime stores and generated indexes are accelerators and must remain rebuildable.

# User Program Interface

User programs may exist in user space.

Examples include Python scripts, notebooks, SQL files, TypeScript utilities, shell scripts, local automation, and role-specific tools.

User programs may read and write user-owned material in `space/`.

User programs should not silently mutate `.workroot/kernel/`. Writes to `.workroot/runtime/` should go through documented drivers or tools.

Durable knowledge promotion should still follow Workroot rules.

External accounts, credentials, and private runtime configuration require explicit privacy handling.

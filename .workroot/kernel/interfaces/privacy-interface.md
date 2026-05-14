# Privacy Interface

Privacy behavior applies to agents, extensions, tools, drivers, exports, and generated stores.

The system must ask confirmation before reading secrets, using external accounts, writing sensitive durable memory, making private material team-visible, deleting, redacting, tombstoning, or writing to kernel space.

Released, redacted, tombstoned, and deleted material must be respected by runtime stores and caches.

v0.9.527 uses permission hints, not a heavy permission system.

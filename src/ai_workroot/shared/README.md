# shared/

`shared/` is a tiny shared kernel.

It may contain stable primitives and standard-library-only contracts that are genuinely cross-cutting, such as:

- `shared/contracts/`
- small extension descriptors
- stable utility types with no capability ownership

It must not become a new `core/` package.

Do not put these here:

- capability models
- protocol policy
- runtime orchestration
- storage-specific business logic
- context recall strategy
- release policy
- Task or Handoff lifecycle logic

If a helper belongs to a capability, keep it in the owning capability module. If several packages want to import it, first check whether it is truly stable and free of Workroot business meaning.

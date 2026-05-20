# Agent Interface

Agent clients are replaceable.

Every agent should follow:

- startup read order
- identity gate behavior
- intent routing behavior
- quick-question behavior
- formal work behavior
- continuation behavior
- save-what-matters behavior
- sensitive confirmation behavior
- private-memory boundary
- writeback expectations
- handoff expectations

The agent is the product interface. The Workroot is the continuity layer.

Agents must not require ordinary users to manage `.workroot/` before useful work begins.

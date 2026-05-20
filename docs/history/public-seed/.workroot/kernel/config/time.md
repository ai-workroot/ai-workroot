# Time Policy

AI Workroot stores temporal values as ISO-8601 text.

This is intentional.

SQLite does not have a dedicated datetime storage class. It supports storing time values as text, real numbers, or integers. AI Workroot chooses text because files and CSV registries are the source of truth.

## Formats

Use one of these formats:

- date: `YYYY-MM-DD`
- instant: `YYYY-MM-DDTHH:MM:SSZ`
- instant with offset: `YYYY-MM-DDTHH:MM:SS+08:00`

Precise instants in machine-readable files should be stored as UTC `Z`.

Agents and scripts may accept user-provided local instants with an explicit offset, such as `2026-05-15T17:00:00+08:00`, but should normalize them to UTC before writing registries, contracts, task records, or generated indexes.

If a local civil time matters to the user, preserve the user's local time and timezone in human-readable notes, such as `2026-05-15 17:00 Asia/Shanghai`, while keeping the machine field in UTC.

Use date-only values for lifecycle fields when day-level precision is enough:

- `created_at`
- `updated_at`
- `review_after`
- `last_used_at`

Use instants when execution timing matters:

- `started_at`
- `ended_at`
- detailed run timestamps

Precise instants without a timezone are not allowed in machine-readable files.

## Why Text

ISO-8601 text is:

- readable in Markdown, CSV, Git diffs, and SQLite
- portable across operating systems and tools
- sortable when the format is consistent
- easy to validate
- easy to export and import

Do not use ambiguous local formats such as `05/14/26`.

Do not use natural language time strings such as `today` or `next week` in registries.

Do not store timezone-free precise instants such as `2026-05-15T17:00:00` in registries or contracts.

Do not use Unix timestamps as the default durable format. They are compact but less readable and less friendly to Git-based review.

## Optional Values

Optional temporal fields may be blank.

If a value is present, it must follow the allowed ISO-8601 formats.

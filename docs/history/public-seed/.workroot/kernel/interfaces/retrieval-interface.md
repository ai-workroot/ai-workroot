# Retrieval Interface

Retrieval drivers help agents find relevant context without loading everything.

They must define searchable scope, ranking method, freshness behavior, lifecycle filtering, privacy filtering, released/tombstone/deleted filtering, explainability expectation, and fallback behavior when indexes are missing.

Vector and graph retrieval are optional accelerators. They must remain subordinate to file-based source truth and registry links.

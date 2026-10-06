---
name: parse-and-structure-logs-with-repeat-counts-and-schema
description: Use when parsing log files containing repeated messages, mixed timestamp formats, and multi-line exceptions to produce a structured JSON output that complies with organizational schema and sorting rules.
---
1. Read the entire log file line by line.
2. Identify log entries by timestamp and log level (case insensitive).
3. Normalize service names by converting to lower-case and replacing '-' with '_'.
4. Convert all timestamps to UTC in the format YYYY-MM-DDTHH:MM:SSZ.
5. Extract only entries with level ERROR or CRITICAL (case insensitive).
6. For each entry:
   - Extract the first line message after the service name and colon.
   - If a traceback follows, extract the last line of the traceback as the exception message; otherwise, set exception to null.
7. Detect and sum repeat counts from lines matching `-- last message repeated N times --` that immediately follow an entry.
8. Aggregate counts by service for the repeat_count field.
9. Sort the final errors array by service name ascending, then by timestamp_utc ascending.
10. Produce a top-level JSON object with:
    - "schema_version": 2
    - "generated_by": "log-triage"
    - "errors": [ ...sorted error entries... ]
11. Verify the number of entries matches expected counts.
12. Validate all fields (timestamp_utc, service, level, message, exception, repeat_count) conform exactly to the schema.
13. Confirm no unrelated tools or dependencies are required.
14. Before submission, run a schema validation or organizational review bot if available.

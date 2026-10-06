---
name: clean-and-validate-data-with-standardized-formatting
description: Use when processing input data files to normalize fields, remove duplicates, convert dates to UTC ISO format, convert monetary values to integer cents, and produce clean CSV and JSON metadata outputs following project conventions.
---
1. Read the input CSV file with appropriate CSV parsing.
2. Normalize categorical fields (e.g., region names) by:
   - Stripping whitespace.
   - Converting to lowercase.
   - Mapping to canonical spellings (e.g., 'north', 'south', 'east', 'west').
3. Parse date/time fields supporting multiple formats (e.g., YYYY-MM-DD, DD/MM/YYYY, ISO-8601 with timezone offsets).
4. Convert all dates to UTC timezone and format as ISO 8601 strings with 'Z' suffix (YYYY-MM-DDTHH:MM:SSZ).
5. Remove duplicate rows based on unique identifiers (e.g., order_id), keeping the first occurrence.
6. Filter out rows with missing or invalid monetary amounts (e.g., sentinel values like -999).
7. Convert all monetary values to integer cents by multiplying by 100 and rounding as needed.
8. Write a clean CSV file with the specified header and one row per distinct valid record.
9. Create a JSON metadata object with keys:
   - "source": input filename string.
   - "rows_in": total number of rows read from input (including duplicates).
   - "rows_used": number of distinct valid rows included in output.
10. Save the JSON metadata and clean CSV to the designated workspace paths.
11. Validate the output files against schema and formatting rules before submission.
12. Document any assumptions or data issues encountered during cleaning.

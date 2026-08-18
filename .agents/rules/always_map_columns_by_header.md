# Rule: Always Map Columns by Header Name (Dynamic Header Mapping)

## Core Requirement
When reading, writing, or updating data on Google Sheets:
1. **NEVER use hardcoded column indexes or hardcoded column letters** (e.g. `col_letter = 'E'`, `row[14]`).
2. **ALWAYS inspect Row 1 headers dynamically** (`header_map = {normalize(h): col_idx}`) and map data dictionary keys to matching column header positions.
3. **Resilience Guarantee**: If columns are reordered, inserted, or removed in Google Sheets, the integration must NEVER shift data or overwrite wrong columns.

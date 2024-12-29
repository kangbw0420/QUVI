import re

def extract_sql_query(text):
    match = re.search(r"(SELECT .*?;\s*)", text, re.DOTALL)
    return match.group(0).strip() if match else None
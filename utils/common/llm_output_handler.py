import re
import logging

logger = logging.getLogger(__name__)

def handle_ai_colon(output: str):
    return re.sub(r"^ai:\s*", "", output, flags=re.IGNORECASE)

def handle_python_code_block(output: str):
    output = output.strip()
    if output.startswith("```python\n"):
        output = output[10:]
    elif output.startswith("```python"):
        output = output[9:]

    if output.endswith("\n```"):
        output = output[:-4]
    elif output.endswith("```"):
        output = output[:-3]
    return output

def handle_sql_code_block(output: str):
    # 1순위: SQL 코드블록
    match = re.search(r"```sql\s*(.*?)\s*```", output, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        # 2순위: WITH 쿼리 (CTE)
        match = re.search(r"WITH.*", output, re.DOTALL)
        if match:
            return match.group(0).strip()
        else:
            # 3순위: SELECT 쿼리
            match = re.search(r"SELECT.*", output, re.DOTALL)
            if match:
                return match.group(0).strip()
            else:
                # 최후: 원본 텍스트 반환
                logger.warning(
                    "No SQL pattern matched, using entire output as SQL query")
                return output

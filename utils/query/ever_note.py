import re
from typing import Dict, Any, Tuple

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from utils.retriever import retriever
from utils.logger import setup_logger
from utils.column.find_column import find_column_conditions

# 모듈별 로거 설정
logger = setup_logger('ever_note')


async def ever_note(query: str) -> Dict[str, Any]:
    """Process trsc query with note1 conditions to find similar notes
    Returns:
        Dict containing:
        - query: Modified SQL query with vector-searched note1 conditions
        - origin_note: Original note value(s) from the query
        - vector_notes: List of vector search results that were applied
    """
    try:
        logger.info(f"Processing query with ever_note: {query[:100]}...")
        ast = sqlglot.parse_one(query, dialect='postgres')

        params = extract_view_function_params(query)
        if not params:
            logger.error("Could not extract function parameters from query")
            return {"query": query, "origin_note": [], "vector_notes": []}

        # Find all note1 conditions in the query using the new module
        note_conditions = find_column_conditions(query, 'note1')

        if not note_conditions:
            logger.info("No note1 conditions found in query")
            return {"query": query, "origin_note": [], "vector_notes": []}

        # Extract original note values
        original_notes = [condition['value'] for condition in note_conditions]

        # Step 2: Create and execute query to get all available notes
        use_intt_id, user_id, company, from_date, to_date = params
        note_query = f"SELECT * FROM aicfo_get_all_note('{use_intt_id}', '{user_id}', '{company}', '{from_date}', '{to_date}')"

        try:
            from core.postgresql import query_execute
            note_results = query_execute(note_query, use_prompt_db=False)
            # 쿼리 실행 결과 리스트로 바꾸기
            available_notes = [note['every_note'] for note in note_results] if note_results else []

            if not available_notes:
                logger.info("No notes found in aicfo_get_all_note result")
                return {"query": query, "origin_note": original_notes, "vector_notes": []}

            # Step 3: Get similar notes for each unique original note
            all_similar_notes = set()
            note_to_similar = {}

            # 중복 note는 한 번만 처리 (set으로 변환하여 고유값만 사용)
            for original_note in set(original_notes):
                # Get similar notes using vector search
                similar_notes = await retriever.get_evernote(
                    original_note,
                    available_notes,
                    top_k=10,
                    threshold=0.1
                )

                note_to_similar[original_note] = similar_notes
                # all_similar_notes는 respondent가 쓰기 위해 저장
                all_similar_notes.update(similar_notes)

            # Step 4: Replace note1 conditions with OR conditions
            for i, condition in enumerate(note_conditions):
                original_note = condition['value']
                similar_notes = note_to_similar.get(original_note, [])

                if not similar_notes:
                    continue

                # Create a new condition with OR for all similar notes
                original_column = condition['node'].this

                # Create ILIKE conditions for each similar note
                or_conditions = []
                for similar_note in similar_notes:
                    # Use ILIKE for case-insensitive matching with wildcards
                    ilike_expr = exp.ILike(
                        this=original_column.copy(),
                        expression=exp.Literal.string(f"%{similar_note}%")
                    )
                    or_conditions.append(ilike_expr)

                # Combine all conditions with OR
                if len(or_conditions) == 1:
                    new_expr = or_conditions[0]
                else:
                    # Create a chain of OR expressions
                    new_expr = or_conditions[0]
                    for i in range(1, len(or_conditions)):
                        new_expr = exp.Or(this=new_expr, expression=or_conditions[i])

                # Wrap OR conditions in parentheses to maintain precedence
                new_expr = exp.Paren(this=new_expr)

                try:
                    replaced = condition['node'].replace(new_expr)
                    logger.info(f"Replacement result: {replaced}")
                except Exception as replace_error:
                    logger.error(f"Error during node replacement: {replace_error}")

            # Generate modified SQL query
            try:
                modified_query = ast.sql(dialect='postgres')
            except Exception as sql_error:
                logger.error(f"Error generating modified SQL: {sql_error}")
                return {"query": query, "origin_note": list(set(original_notes)),
                        "vector_notes": list(all_similar_notes)}

            # 최종 결과에는 고유한 노트값만 반환
            result = {
                "query": modified_query,
                "origin_note": list(set(original_notes)),
                "vector_notes": list(all_similar_notes)
            }

            logger.info(f"Found similar notes: {all_similar_notes}")
            return result

        except Exception as exec_error:
            logger.error(f"Error executing note query: {exec_error}")
            return {"query": query, "origin_note": list(set(original_notes)), "vector_notes": []}

    except ParseError as e:
        logger.error(f"SQL parsing error in ever_note: {e}")
        return {"query": query, "origin_note": [], "vector_notes": []}
    except Exception as e:
        logger.error(f"Error in ever_note: {e}")
        return {"query": query, "origin_note": [], "vector_notes": []}

def extract_view_function_params(query: str) -> Tuple[str, str, str, str, str]:
    # Using re.IGNORECASE to make the pattern case-insensitive
    pattern = r"(?i)aicfo_get_all_\w+\('([^']+)', '([^']+)', '([^']+)', '([^']+)', '([^']+)'\)"
    match = re.search(pattern, query)

    if match:
        use_intt_id = match.group(1)
        user_id = match.group(2)
        company = match.group(3)
        from_date = match.group(4)
        to_date = match.group(5)
        return (use_intt_id, user_id, company, from_date, to_date)

    return None
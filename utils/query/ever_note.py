import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from utils.retriever import retriever
import asyncio
from typing import Dict, List, Any, Set, Tuple, Optional
import re
from utils.logger import setup_logger
from graph.task.executor import execute

logger = setup_logger('evernote')

async def ever_note(query: str, main_com: str) -> Dict[str, Any]:
    """
    Process trsc query with note1 conditions to find similar notes
    
    Flow:
    1. Check if query has note1 conditions
    2. Extract the original notes and parameters from the query
    3. Call aicfo_get_all_note view function to get all available notes
    4. Use vector search to find similar notes for each original note
    5. Replace note1 conditions with OR conditions for all similar notes
    6. Return modified query and note information
    
    Args:
        query: Original SQL query
        main_com: Main company name
        
    Returns:
        Dict containing:
        - query: Modified SQL query with vector-searched note1 conditions
        - origin_note: Original note value(s) from the query
        - vector_notes: List of vector search results that were applied
    """
    try:
        # Parse the SQL query
        ast = sqlglot.parse_one(query, dialect='postgres')
        
        # Extract function parameters from the original query
        params = extract_view_function_params(query)
        if not params:
            logger.error("Could not extract function parameters from query")
            return {"query": query, "origin_note": [], "vector_notes": []}
        
        def find_note_conditions(ast: exp.Expression) -> List[Dict]:
            """
            AST에서 모든 note1 조건을 찾아 반환
            
            노드 ID를 기반으로 이미 처리한 노드를 추적하여 중복 처리를 방지
            """
            note_conditions: List[Dict] = []
            visited_nodes = set()
            
            def process_node(node):
                # 이미 방문한 노드는 처리하지 않음
                node_id = id(node)
                if node_id in visited_nodes:
                    return
                visited_nodes.add(node_id)
                
                # note1 조건인지 확인
                if isinstance(node, (exp.EQ, exp.Like, exp.ILike)):
                    if (isinstance(node.this, exp.Column) and 
                        node.this.name == 'note1'):
                        # 값 추출
                        if isinstance(node.expression, exp.Literal):
                            note_str = str(node.expression.this).strip("'%")
                        else:
                            note_str = str(node.expression).strip("'%")
                        
                        # 조건 정보 저장
                        note_conditions.append({
                            'type': type(node).__name__,
                            'value': note_str,
                            'node': node
                        })
                
                # 자식 노드 처리 (arguments 메서드 사용)
                for arg_name, arg_value in node.args.items():
                    if isinstance(arg_value, exp.Expression):
                        process_node(arg_value)
                    elif isinstance(arg_value, list):
                        for item in arg_value:
                            if isinstance(item, exp.Expression):
                                process_node(item)
            
            # 루트 노드부터 시작
            process_node(ast)
            
            return note_conditions
        
        # Find all note1 conditions in the query (using our improved function)
        note_conditions = find_note_conditions(ast)
        
        if not note_conditions:
            logger.info("No note1 conditions found in query")
            return {"query": query, "origin_note": [], "vector_notes": []}
        
        # Extract original note values
        original_notes = [cond['value'] for cond in note_conditions]
        logger.info(f"Found {len(note_conditions)} note1 conditions with {len(set(original_notes))} unique values: {original_notes}")
        
        # Step 2: Create and execute query to get all available notes
        use_intt_id, user_id, company, from_date, to_date = params
        note_query = f"SELECT * FROM aicfo_get_all_note('{use_intt_id}', '{user_id}', '{company}', '{from_date}', '{to_date}')"
        
        logger.info(f"Executing note query: {note_query}")
        try:
            # Execute query to get all available notes
            available_notes = execute(note_query)
            
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
                    top_k=3
                )
                
                note_to_similar[original_note] = similar_notes
                all_similar_notes.update(similar_notes)
                logger.info(f"Found {len(similar_notes)} similar notes for '{original_note}': {similar_notes}")
            
            # Step 4: Replace note1 conditions with OR conditions
            for condition in note_conditions:
                original_note = condition['value']
                similar_notes = note_to_similar.get(original_note, [])
                
                if not similar_notes:
                    # No similar notes found, keep original condition
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
                
                # Replace the old condition with the OR chain
                condition['node'].replace(new_expr)
            
            # Generate modified SQL query
            modified_query = ast.sql(dialect='postgres')
            
            # 최종 결과에는 고유한 노트값만 반환
            return {
                "query": modified_query,
                "origin_note": list(set(original_notes)),  # 중복 제거
                "vector_notes": list(all_similar_notes)
            }
            
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
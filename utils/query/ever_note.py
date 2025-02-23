import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from utils.retriever import retriever
import asyncio
from typing import Dict, List, Optional

async def ever_note(query: str, main_com: str) -> str:
    """Analyze SQL query for note1 conditions and modify them using vector search
    Returns:
        Modified SQL query with vector-searched note1 conditions
    """
    try:
        # Parse the SQL query
        ast = sqlglot.parse_one(query, dialect='postgres')
        note_conditions: List[Dict] = []
        processed_notes: Dict[str, Optional[str]] = {}  # Cache for vector search results
        
        def find_note_conditions(node: exp.Expression) -> None:
            """Recursively find note1 conditions in the AST"""
            if isinstance(node, (exp.EQ, exp.Like)):
                if (isinstance(node.this, exp.Column) and 
                    node.this.name == 'note1'):
                    # Extract note value, handling both direct strings and expressions
                    if isinstance(node.expression, exp.Literal):
                        note_str = str(node.expression.this).strip("'%")
                    else:
                        note_str = str(node.expression).strip("'%")
                        
                    note_conditions.append({
                        'type': 'EQ' if isinstance(node, exp.EQ) else 'LIKE',
                        'value': note_str,
                        'node': node
                    })
            
            # Recursively process child nodes
            for child in node.walk():
                if child is not node:
                    find_note_conditions(child)
        
        # Find all note1 conditions in the query
        find_note_conditions(ast)
        
        if not note_conditions:
            return query
            
        # Process unique note values to avoid duplicate vector searches
        for condition in note_conditions:
            note_str = condition['value']
            
            # Skip if we've already processed this note string
            if note_str in processed_notes:
                vector_note = processed_notes[note_str]
            else:
                try:
                    # Vector search with timeout
                    similar_notes = await asyncio.wait_for(
                        retriever.get_evernote(note_str, main_com),
                        timeout=5.0
                    )
                    
                    # Cache the result
                    vector_note = similar_notes[0] if similar_notes else None
                    processed_notes[note_str] = vector_note
                    
                except (asyncio.TimeoutError, Exception) as e:
                    print(f"Vector search error for note1 '{note_str}': {str(e)}")
                    continue
            
            # Skip if no vector match found
            if not vector_note:
                continue
                
            # Create new node preserving the original column reference
            original_column = condition['node'].this
            if condition['type'] == 'LIKE':
                new_expr = exp.Like(
                    this=original_column,  # Preserve original column reference
                    expression=exp.Literal.string(f"%{vector_note}%")
                )
            else:  # EQ
                new_expr = exp.EQ(
                    this=original_column,  # Preserve original column reference
                    expression=exp.Literal.string(vector_note)
                )
            
            # Replace the old condition
            condition['node'].replace(new_expr)
        
        # Generate modified SQL query with preserved formatting
        modified_query = ast.sql(dialect='postgres')
        return modified_query
        
    except ParseError as e:
        print(f"SQL parsing error in ever_note: {e}")
        return query
    except Exception as e:
        print(f"Error in ever_note: {e}")
        return query
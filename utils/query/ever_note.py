import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from utils.retriever import retriever
import asyncio

async def ever_note(query: str, main_com: str) -> str:
    """Analyze SQL query for note1 conditions and modify them using vector search if no results found
    Returns:
        Modified SQL query with vector-searched note1 conditions, or original query if no results found
        or if vector search fails/times out
    """
    try:
        # Parse the SQL query
        ast = sqlglot.parse_one(query, dialect='postgres')
        note_conditions = []
        
        def find_note_conditions(node: exp.Expression):
            """Recursively find note1 conditions in the AST"""
            if isinstance(node, (exp.EQ, exp.Like)):
                if (isinstance(node.this, exp.Column) and 
                    node.this.name == 'note1'):
                    # Extract the note string value
                    note_str = str(node.expression.this).strip("'%")
                    note_conditions.append({
                        'type': 'EQ' if isinstance(node, exp.EQ) else 'LIKE',
                        'value': note_str,
                        'node': node
                    })
            
            # Continue traversing the AST
            for child in node.walk():
                if child is not node:
                    find_note_conditions(child)
        
        # Find all note1 conditions in the query
        find_note_conditions(ast)
        
        if not note_conditions:
            return query
            
        # Get vector matches for each note condition
        for condition in note_conditions:
            note_str = condition['value']
            try:
                # Use vector search with timeout
                similar_notes = await asyncio.wait_for(
                    retriever.get_evernote(note_str, main_com),
                    timeout=5.0  # 5초 타임아웃
                )
                
                if similar_notes:
                    # Get the most similar note
                    vector_note = similar_notes[0]
                    
                    # Create new condition node based on original condition type
                    if condition['type'] == 'LIKE':
                        new_expr = exp.Like(
                            this=exp.Column(this=None, name='note1'),
                            expression=exp.Literal.string(f"%{vector_note}%")
                        )
                    else:  # EQ
                        new_expr = exp.EQ(
                            this=exp.Column(this=None, name='note1'),
                            expression=exp.Literal.string(vector_note)
                        )
                    
                    # Replace the old condition with the new one
                    condition['node'].replace(new_expr)
                    
            except asyncio.TimeoutError:
                print(f"Vector search timed out for note1: {note_str}")
                continue  # Skip this condition and keep the original
            except Exception as e:
                print(f"Vector search failed for note1: {note_str} with error: {str(e)}")
                continue  # Skip this condition and keep the original
        
        # Generate modified SQL query
        modified_query = ast.sql(dialect='postgres')
        return modified_query
        
    except ParseError as e:
        print(f"SQL parsing error in ever_note: {e}")
        return query
    except Exception as e:
        print(f"Error in ever_note: {e}")
        return query
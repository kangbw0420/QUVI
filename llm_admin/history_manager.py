from typing import List, Any

from core.postgresql import query_execute
from utils.logger import setup_logger

logger = setup_logger("history_manager")


def get_history(
    chain_id: str, state_history: List[str], node_type: str, limit: int = 5
) -> dict:
    """Retrieve conversation history grouped by chain_id.
    Example:
        get_history("chain123", ["user_question", "sql_query", "final_answer"])
        {
            "chain123": [
                {
                    "user_question": "What were our sales last month?",
                    "sql_query": "SELECT SUM(amount) FROM sales WHERE date >= '2023-01-01'",
                    "final_answer": "Total sales were $50,000"
                }
            ],
            "chain456": [
                {
                    "user_question": "What's our current inventory?",
                    "sql_query": "SELECT product_name, quantity FROM inventory",
                    "final_answer": "Current inventory: Product A (100 units), Product B (50 units), ..."
                }
            ]
        }
    """
    try:
        selected_columns = ", ".join(f"s.{col}" for col in state_history)
        node_type_condition = f"t.node_type = '{node_type}'"

        join_query = f"""
        WITH latest_chains AS (
            SELECT {selected_columns}, c.id as chain_id, c.chain_start
            FROM state s
            JOIN trace t ON s.trace_id = t.id
            JOIN "chain" c ON t.chain_id = c.id
            WHERE c.conversation_id = (
                SELECT conversation_id 
                FROM "chain" 
                WHERE id = %s
            )
            AND {node_type_condition}
            ORDER BY c.chain_start DESC
            LIMIT %s
        )
        SELECT *
        FROM latest_chains
        ORDER BY chain_start ASC
        """

        params = [chain_id, limit]

        result = query_execute(join_query, params, use_prompt_db=True)

        # query_execute가 boolean을 반환하는 경우 처리
        if isinstance(result, bool):
            logger.info("Query returned boolean value, treating as empty result")
            return {}

        if not result:
            logger.warning(f"No history found for chain_id: {chain_id}")
            return {}

        # Group results by chain_id
        history_by_chain = {}
        for row in result:
            chain_id = row.pop("chain_id")
            if chain_id not in history_by_chain:
                history_by_chain[chain_id] = []
            history_by_chain[chain_id].append(row)

        logger.info(f"Processed history: {history_by_chain}")
        return history_by_chain

    except Exception as e:
        logger.error(f"Error in get_history: {str(e)}")
        return {}


def get_nth_history(chain_id: str, column: str, n: int = 1) -> Any:
    """Get the nth most recent history for a given chain_id and column.
    Args:
        chain_id: The chain ID to get history for
        column: The column to retrieve from state table
        n: The position from most recent (1 = most recent, 2 = second most recent, etc.)
    Returns:
        The value of the specified column for the nth most recent history, or None if not found
        Returns the original type from database (e.g., jsonb as dict/list, text as str, etc.)
    """
    query = f"""
    SELECT s.{column}
    FROM state s
    JOIN trace t ON s.trace_id = t.id
    JOIN "chain" c ON t.chain_id = c.id
    WHERE c.conversation_id = (
        SELECT conversation_id 
        FROM "chain" 
        WHERE id = %s
    )
    AND s.{column} IS NOT NULL
    ORDER BY s.id DESC
    LIMIT %s
    """

    params = [chain_id, n]
    result = query_execute(query, params, use_prompt_db=True)

    if not result:
        logger.warning(f"No history found for chain_id: {chain_id}, column: {column}")
        return None

    result_dict = result[n - 1]  # Convert to 0-based index
    return result_dict.get(column)


def get_recent_history(chain_id: str, column: str) -> Any:
    return get_nth_history(chain_id, column, n=1)


def get_former_history(chain_id: str, column: str) -> Any:
    return get_nth_history(chain_id, column, n=2)

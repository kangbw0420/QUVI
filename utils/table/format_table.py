from typing import List, Dict, Any
from utils.logger import setup_logger

logger = setup_logger('format_table')

def format_table_pipe(data: List[Dict[str, Any]]) -> str:
    """
    데이터를 파이프(|) 형식의 표로 변환.
    10행 초과 시 상위 5개 + 하위 5개를 출력하고, 중간은 생략 메시지로 표시.
    """
    try:
        if not data:
            return "(데이터 없음)"

        # 데이터 평탄화
        flattened_data = []
        for item in data:
            if isinstance(item, dict):
                if 'data' in item and isinstance(item['data'], list):
                    flattened_data.extend(item['data'])
                else:
                    flattened_data.append(item)

        processed_data = flattened_data if flattened_data else data

        # 사용 가능한 컬럼 필터링
        available_columns = [col for col in columns if any(col in row for row in processed_data)]
        if not available_columns and processed_data:
            available_columns = list(processed_data[0].keys())[:5]

        # 헤더 생성
        table = " | ".join(available_columns) + "\n"
        table += "-" * (sum(len(col) for col in available_columns) + (len(available_columns) - 1) * 3) + "\n"

        total_rows = len(processed_data)

        # ✅ 행 개수에 따라 출력 방식 결정
        if total_rows <= 10:
            display_rows = processed_data
        else:
            display_rows = processed_data[:5] + [{"__ellipsis__": True}] + processed_data[-5:]

        # 행 출력
        for row in display_rows:
            if row.get("__ellipsis__"):
                table += "... (중간 생략) ...\n"
                continue
            row_values = [str(row.get(col, "")) for col in available_columns]
            table += " | ".join(row_values) + "\n"

        return table

    except Exception as e:
        logger.error(f"Error formatting table: {str(e)}", exc_info=True)
        return f"(테이블 형식 변환 오류: {str(e)})"


def format_table_html(data: List[Dict[str, Any]], columns: List[str]) -> str:
    """
    데이터를 HTML 표 형식으로 변환
    """
    if not data or not columns:
        return ""

    # 테이블 시작과 헤더 행
    table = "<table>\n<tr>"
    for col in columns:
        table += f"<th>{col}</th>"
    table += "</tr>\n"

    # 데이터 행 추가
    for row in data:
        table += "<tr>"
        for col in columns:
            cell_value = row.get(col, "")
            table += f"<td>{cell_value}</td>"
        table += "</tr>\n"

    # 테이블 종료
    table += "</table>"

    return table
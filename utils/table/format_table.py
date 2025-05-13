from typing import List, Dict, Any

def format_table_pipe(data):
    """
    데이터를 파이프(|) 형식의 표로 변환.
    10행 초과 시 상위 5개 + 하위 5개를 출력하고, 중간은 생략 메시지로 표시.
    """
    try:
        # 튜플 처리 - 튜플에 단일 리스트가 있는 경우 추출
        if isinstance(data, tuple) and len(data) == 1:
            data = data[0]
            
        # 입력이 리스트가 아니면 변환 시도
        if not isinstance(data, list):
            try:
                data = list(data)
            except:
                return "(변환할 수 없는 데이터 형식)"
        
        # 빈 데이터 확인
        if not data:
            return "(데이터 없음)"
            
        # 중첩 데이터 간단 확인 (data 키가 있고 그 안에 리스트가 있는 경우만 처리)
        if isinstance(data[0], dict) and 'data' in data[0] and isinstance(data[0]['data'], list):
            flat_data = []
            for item in data:
                if 'data' in item and isinstance(item['data'], list):
                    flat_data.extend(item['data'])
            data = flat_data if flat_data else data

        # 데이터 형식 확인
        if not data or not isinstance(data[0], dict):
            return "(유효한 데이터 형식이 아님)"

        # 첫 번째 데이터 항목에서 키를 가져와 헤더로 사용
        headers = list(data[0].keys())
        
        # 헤더 생성
        table = " | ".join(headers) + "\n"
        table += "-" * (sum(len(col) for col in headers) + (len(headers) - 1) * 3) + "\n"

        total_rows = len(data)

        # 행 개수에 따라 출력 방식 결정
        if total_rows <= 10:
            display_rows = data
        else:
            display_rows = data[:5] + [{"__ellipsis__": True}] + data[-5:]

        # 행 출력
        for row in display_rows:
            if row.get("__ellipsis__"):
                table += "... (중간 생략) ...\n"
                continue
            row_values = [str(row.get(col, "")) for col in headers]
            table += " | ".join(row_values) + "\n"

        return table

    except Exception as e:
        return f"(테이블 형식 변환 오류: {str(e)})"

def format_table_html(data):
    """
    데이터를 HTML 표 형식으로 변환
    """
    try:
        # 튜플 처리 - 튜플에 단일 리스트가 있는 경우 추출
        if isinstance(data, tuple) and len(data) == 1:
            data = data[0]
            
        # 입력이 리스트가 아니면 변환 시도
        if not isinstance(data, list):
            try:
                data = list(data)
            except:
                return "<table><tr><td>(변환할 수 없는 데이터 형식)</td></tr></table>"
        
        # 빈 데이터 확인
        if not data:
            return "<table><tr><td>(데이터 없음)</td></tr></table>"
            
        # 중첩 데이터 간단 확인
        if isinstance(data[0], dict) and 'data' in data[0] and isinstance(data[0]['data'], list):
            flat_data = []
            for item in data:
                if 'data' in item and isinstance(item['data'], list):
                    flat_data.extend(item['data'])
            data = flat_data if flat_data else data

        # 데이터 형식 확인
        if not data or not isinstance(data[0], dict):
            return "<table><tr><td>(유효한 데이터 형식이 아님)</td></tr></table>"

        # 첫 번째 데이터 항목에서 키를 가져와 헤더로 사용
        headers = list(data[0].keys())

        # 테이블 시작과 헤더 행
        table = "<table>\n<tr>"
        for col in headers:
            table += f"<th>{col}</th>"
        table += "</tr>\n"

        # 데이터 행 추가 (최대 10행)
        total_rows = len(data)
        display_rows = data[:10] if total_rows > 10 else data
        
        for row in display_rows:
            table += "<tr>"
            for col in headers:
                cell_value = row.get(col, "")
                table += f"<td>{cell_value}</td>"
            table += "</tr>\n"
            
        # 생략 표시
        if total_rows > 10:
            table += f"<tr><td colspan='{len(headers)}'>... 외 {total_rows - 10}행 생략 ...</td></tr>\n"

        # 테이블 종료
        table += "</table>"

        return table

    except Exception as e:
        return f"<table><tr><td>테이블 형식 변환 오류: {str(e)}</td></tr></table>"
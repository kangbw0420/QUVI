## Agent Architecture
```mermaid
stateDiagram-v2
    [*] --> next_page
    next_page --> checkpoint
    next_page --> END: user_question == "next_page"

    checkpoint --> isapi: not is_joy
    checkpoint --> killjoy: is_joy
    
    isapi --> funk: is_api
    isapi --> nl2sql: not is_api
    
    funk --> params
    params --> yqmd: selected_api == "aicfo_get_financial_flow"
    params --> executor: selected_api != "aicfo_get_financial_flow"
    params --> END: invalid_date
    
    yqmd --> executor
    
    nl2sql --> executor
    
    executor --> nodata: no_data
    executor --> respondent: not no_data and not note_changed and not query_error
    executor --> END: note_changed
    executor --> safeguard: query_error and safe_count < 2
    executor --> END: invalid_date
    
    safeguard --> executor
    
    killjoy --> END
    nodata --> END
    respondent --> END
```



## 환경설정
가상환경 설정 및 dependancy 설치 
(macOS)  
```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install requirements.txt
```

(Window PowerShell)  
```
python -m venv venv
.\venv\Scripts\Activate
python -m pip install -r requirements.txt
```

(Window cmd)  
```
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

## 주석 스타일(자세함보다는 효율성)
    """(따옴표에 붙여서, 되도록이면 한 줄로, 불필요한 줄바꿈 no) 함수에 대한 간단한 설명
    Args: 헷갈릴 경우 적지만, 함수 정의에서 알아볼 수 있을 경우 되도록 적지 않습니다
    Returns:
    Raises:
    """

## 연락처
궁금하신 사항이 있으실 때는 / 혹은 오류가 있을 때는 아래의 번호로 언제든 연락 부탁드립니다. :blush:  
윤주호 010-3168-7616 / yoonjuho92@gmail.com  
김하정 010-2098-1433 / kabigonmaniac@gmail.com

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

## 주석 스타일(파이썬은 알아보기 쉬우므로, 자세함보다는 효율성을 추구)
    """(따옴표에 붙여서, 되도록이면 한 줄로, 불필요한 줄바꿈 no) 함수에 대한 간단한 설명
    Args: 헷갈릴 경우 적지만, 함수 정의에서 알아볼 수 있을 경우 되도록 적지 않습니다
    Returns:
    Raises:
    """
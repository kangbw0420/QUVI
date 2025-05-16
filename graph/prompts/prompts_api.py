PROMPT_FUNK = '''당신은 사용자의 질문을 분석하여 데이터베이스 쿼리에 필요한 요소들을 파악하는 전문가입니다.
사용자의 질문에 답하기 위해 어떤 테이블을 조회해야 할지 선택하여 테이블 이름만 출력하세요.

aicfo_get_financial_status와 aicfo_get_available_fund는 한 시점의 데이터만 조회합니다.
aicfo_get_variation_status는 두 시점 간의 데이터를 비교합니다.
aicfo_get_monthly_flow는 특정 기간 동안의 흐름을 보고 싶을 때 사용합니다. 특정 기간은 최소 두 달 이상입니다.

**사용자의 질문이 미래 시점을 조회할 경우 오늘 날짜({today})로 조회합니다." 

당신이 답할 수 있는 옵션은 다음과 같습니다. 반드시 aicfo_get_variation_status / aicfo_get_financial_status / aicfo_get_monthly_flow / aicfo_get_available_fund 중 하나만 답해야 합니다.
- aicfo_get_variation_status: 자금변동현황
- aicfo_get_financial_status: 자금현황
- aicfo_get_monthly_flow: 월간자금흐름
- aicfo_get_available_fund: 가용자금

아래 예시를 참고하세요.'''


PROMPT_PARAMS = '''당신은 사용자 질문에서 날짜 정보를 추출하는 전문가입니다. 

다음 사용자의 질문에 답하기 위해서 필요한 날짜값 두 개를 추출해주세요.

aicfo_get_financial_status, aicfo_get_available_fund는 시점 데이터이기 때문에 하나의 날짜만을 골라야합니다. aicfo_get_variation_status, aicfo_get_monthly_flow은 서로 다른 두 개의 날짜값을 골라야합니다.

1. 특정 날짜 또는 기간을 말한 경우
사용자가 특정 날짜 또는 기간을 말한 경우, 오늘 날짜({today})를 기준으로 사용자가 조회할 적절한 날짜를 판단해서 넣어주세요.

2. 특정 날짜 또는 기간 표현이 없는 경우

1) aicfo_get_financial_status, aicfo_get_available_fund
오늘 날짜({today})를 조회합니다.

2) aicfo_get_variation_status
오늘 날짜({today})와 1개월 전 날짜를 조회합니다.

3) aicfo_get_monthly_flow
오늘 날짜({today})와 6개월 전 날짜를 조회합니다.

3. 2월 윤일(leap day) 처리
1) 2월의 마지막 날을 처리할 때는 윤년 여부를 확인해야 합니다:
- 2024년, 2028년, 2032년 등 4로 나누어 떨어지는 해의 2월은 29일까지 있습니다.
- 그 외의 해의 2월은 28일까지만 있습니다.
- 2월 마지막 날을 참조할 때는 해당 연도의 윤년 여부를 반드시 확인하세요.

2) 예시: 오늘이 2025년 3월 15일일 때,
- "2월 잔액" → 2025년 2월 28일 (2025년은 윤년이 아니므로 28일까지)
- "2024년 2월 잔액" → 2024년 2월 29일 (2024년은 윤년이므로 29일까지)

다음의 데이터를 담은 같은 JSON 형태로 답변해 주세요.
반드시 JSON형식의 답변만 출력해야 합니다.

## JSON 형태
{json_format}'''
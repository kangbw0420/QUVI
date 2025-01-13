import requests
import json
import time

def test_korean_questions():
    # 테스트할 한글 질문들
    questions = [
        "오늘 거래내역"
    ]

    for question in questions:
        print(f"\n테스트 질문: {question}")

        payload = {
            "user_question": question,
            "user_id": "default_user",
            "session_id": "DEV_SESSION_ID",# DEV_SESSION_ID=꼬리물기 및 DB저장 X,  f0e89beb-eac9-4d8e-bff9-79a83f1b2b5a
        }

        try:
            response = requests.post(
                "http://localhost:8000/process",
                headers={"Content-Type": "application/json; charset=utf-8"},
                json=payload
            )
            
            # 응답 결과를 JSON 문자열로 변환
            response_str = json.dumps(response.json(), ensure_ascii=False, indent=2)
            # 1000자로 제한하고 잘렸다는 것을 표시
            if len(response_str) > 1000:
                print("응답 결과:", response_str[:1000] + "...")
            else:
                print("응답 결과:", response_str)
            
        except Exception as e:
            print("오류 발생:", str(e))

        time.sleep(2)  # 요청 간 간격

if __name__ == "__main__":
    test_korean_questions()
'''
[시험 범위]
<기본 질의>
계좌잔액(수시입출 계좌 잔액)
거래내역(오늘 거래내역)
대출현황(=차입금 현황, 오늘 기준 대출 잔고)
예적금 잔액(오늘 기준 예적금 잔고)
외화 잔액
외화 거래내역

<상세 질의>
은행별 잔액 보여줘
평균 대출 금리 알려줘
기업은행 계좌 거래내역 상세하게 보여줘
1억 이상 수시입출 거래내역 보여줘
XX 거래처 돈 들어왔어?(or 쿠콘한테 돈 나갔어?)
이번 달 급여 나갔어?
평균 대출 금리 알려줘
대출 금리 높은 순으로 알려줘
3개월 이내에 만기 도래하는 차입금 있어?
예금 금리 얼마야?

<통합 질의>
자금현황(갖고 있는 돈의 전체)
가용자금(현재 내가 쓸 수 있는 돈. 3년짜리 적금 이런건 빼야함. 1세대 기준 차용)
계열사별 자금 현황

<분석 질의>
자금 변동 현황(전일 대비 자금 변동 현황)
지난 달 순수익 얼마야?(지난 달 현금 흐름 어때)
월별 현금 흐름
월별 급여 추이
올해 가장 입금이 많이 된 거래처가 어디야
지난 달 지출된 돈 중에 가장 큰게 뭐야?
우리 연구비 비중이 어떻게 돼?(인건비 비중이 어떻게 돼?)

<꼬리 질문>
작년 12월 현금 흐름 보여줘? -> 11월도
이번 달 지출이 지난 달하고 비교해서 어때? -> (늘었음) 왜 늘었어?/(줄었음) 왜 줄었어?
웹케시 그룹 전체 자금 현황 보여줘 -> 쿠콘은 어떻게 돼?

<ML> 이건 일단은 아니고 나중에
정기성 매출과 비정기성 매출이 어떻게 돼?
올 연말 가용 자금 어떻게 될 것 같아?
'''
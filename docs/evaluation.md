# 사고유형 AI 정량평가와 안전한 Abstention

## 평가 계약

사고유형 분류는 L1 8개(`INJ/ILL/PROP/LIA/TRV/CHG/EMG/SPC`)와 각 L1 아래의 L2를
대상으로 한다. `confidence`는 정답 확률로 해석하지 않고 **자동 분류할지, 추가 질문으로
보낼지를 결정하는 라우팅 신호**로만 사용한다.

운영 안전 규칙은 다음과 같다.

1. Gemini 비활성화, 빈 입력, API 오류, 불완전한 응답에서는 임의의 L2를 선택하지 않는다.
2. L1 confidence가 `0.40` 미만이면 해당 L1 루트에 보류하고 L2 호출을 생략한다.
3. L2 confidence가 `0.80` 미만이면 해당 L1 루트에 보류한다.
4. 모델이 새 유형을 제안해도 검수 전에는 사고에 자동 할당하지 않는다.
5. L1 루트로 보류된 사고는 기존 `pending_questions` 흐름으로 넘어가 사고유형별 추가 질문을 받는다.
6. 낮은 L1 confidence로 보류된 사고는 후속 답변을 최초 서술과 합쳐 L1부터 다시 분류한다.

기본 임계값은 incident-eval-v2의 calibration 80건에서 선택하고 held-out 80건으로 확인한
값이다. 배포 모델이나 프롬프트가 바뀌면 아래 골드셋 평가로 다시 선정해야 한다.

## 골드셋

`backend/data/eval/incidents_gold.jsonl`에는 L1별 20건, 총 160건이 있다.

| 구분 | 건수 |
|---|---:|
| L1 8개 클래스 | 각 20 |
| easy | 70 |
| hard | 56 |
| ambiguous | 34 |
| L1 abstain 대상 | 8 |
| L2 abstain 대상 | 34 |
| calibration / evaluation | 80 / 80 |
| 합계 | 160 |

각 행은 `id`, `text`, `gold_l1`, `gold_l2`, `difficulty`, `expected_l1_abstain`,
`expected_l2_abstain`, `split`을 가진다. L1도 판단할 수 없는 사례 8건과, L1은 알지만 L2를
확정할 수 없는 사례를 분리했다. L2 abstain 대상 34건은 `gold_l2=null`이다. 이 파일은
개인정보가 없는 합성 평가 문장만 포함한다.

`split`은 각 L1의 홀수 ID 10건을 calibration, 짝수 ID 10건을 evaluation으로 배치한다.
따라서 두 집합은 각각 80건이고 L1별 10건씩 유지된다. calibration은 임계값 선택에만,
evaluation은 선택된 임계값의 최종 성능 보고에만 사용한다.

## 실행

백엔드 디렉터리에서 다음과 같이 실행한다.

```bash
python -m eval.evaluate_incident_classifier --validate-only \
  --output eval/results/incident_eval.validation.json
```

위 명령은 API를 호출하지 않고 스키마, 8개 클래스 포함 여부, 분포만 검증한다.

`GEMINI_API_KEY`가 설정된 평가 환경에서는 라이브 예측과 정량평가를 실행한다.

```bash
python -m eval.evaluate_incident_classifier \
  --request-interval 4.2 \
  --retry-wait 65 \
  --checkpoint /tmp/incident-eval-predictions.json \
  --output eval/results/incident_eval.json
```

기본 요청 간격은 무료 티어의 분당 호출 제한을 넘지 않도록 4.2초다. 429 응답은 65초 후
최대 5회 재시도하며, 다른 API 오류는 평가값으로 바꾸지 않고 즉시 실패시킨다. `--checkpoint`를
지정하면 사례별 원시 예측을 저장하므로 장시간 실행이 중단돼도 완료 지점부터 재개할 수 있다.

결과 JSON에는 모델명, 프롬프트·골드셋 SHA-256, 평가 버전, 생성 시각, 원시 예측과 다음 지표가 기록된다.

- L1 Accuracy, Macro-F1, coverage, confusion matrix(ABSTAIN 열 포함)
- L2 end-to-end Accuracy와 Macro-F1
- L1을 맞힌 표본에 대한 L2 conditional Accuracy와 Macro-F1
- Abstention precision, recall, F1
- L1/L2 각각 confidence `0.40`~`0.80` 구간의 `0.05` 단위 2차원 grid search(81조합)
- calibration 80건에서 선택한 임계값의 held-out evaluation 80건 성능
- 코드에 설정된 운영값의 held-out 성능을 별도로 기록

원시 예측이 든 기존 결과를 재사용하면 API를 다시 호출하지 않고 평가 계산만 재현할 수 있다.

```bash
python -m eval.evaluate_incident_classifier \
  --predictions eval/results/incident_eval.json \
  --output eval/results/incident_eval.recomputed.json
```

## 임계값 선정과 해석

평가 도구는 calibration 집합에서 각 L1/L2 임계값 조합의
`L1 abstention F1 + L2 abstention F1 + L2 end-to-end Macro-F1`이 가장 큰 지점을 우선하고,
동률이면 abstention recall 합계와 더 높은 임계값을 선택한다. 금융 안내에서는 오분류가
불필요한 담보 안내로 이어질 수 있으므로 애매한 사례를 질문으로 되돌리는 recall을 동률
기준으로 둔다. 선택된 조합의 최종 수치는 held-out evaluation 집합에서 한 번만 계산한다.

다만 이 선택은 운영 정책의 대체물이 아니다. 모델 또는 프롬프트 변경 시 결과 JSON을 새로 남기고,
오분류 비용과 질문 증가 비용을 함께 검토한 뒤 `DEFAULT_L1_AUTO_THRESHOLD`와
`DEFAULT_L2_AUTO_THRESHOLD`를 갱신한다.

## 현재 저장된 결과

`backend/eval/results/incident_eval.json`에 Gemini `gemini-3.5-flash-lite`의 실제 160건 원시
예측과 평가 결과를 저장했다. calibration에서 선택된 임계값은 L1 `0.40`, L2 `0.80`이며,
held-out evaluation 80건의 결과는 다음과 같다.

| 지표 | 결과 |
|---|---:|
| L1 Accuracy | 0.9474 |
| L1 Macro-F1 | 0.9639 |
| L1 Coverage | 0.9605 |
| L2 End-to-End Accuracy | 0.9839 |
| L2 End-to-End Macro-F1 | 0.9885 |
| L2 Accuracy given correct L1 | 1.0000 |
| L2 Macro-F1 given correct L1 | 1.0000 |
| L1 Abstention Precision / Recall / F1 | 0.5714 / 1.0000 / 0.7273 |
| L2 Abstention Precision / Recall / F1 | 0.9444 / 0.9444 / 0.9444 |

기존 운영 초기값 `0.65/0.70`과 비교하면 held-out L1 Accuracy는 `0.9342 → 0.9474`, L1
abstention F1은 `0.6154 → 0.7273`으로 개선됐으며 L2 Accuracy와 Macro-F1은 동일했다.
이에 따라 코드 기본값도 선택된 `0.40/0.80`으로 갱신했다.

`backend/eval/results/incident_eval.validation.json`은 API를 호출하지 않는 골드셋 구조 검증
결과다. 이 파일의 `metrics=null`은 모델 성능 미측정이 아니라 validation-only 실행의 의미이며,
실제 성능 수치는 위 `incident_eval.json`을 기준으로 한다.

## 회귀 테스트

```bash
pytest -q backend/tests/test_incident_classifier_fallback.py \
  backend/tests/test_incident_classifier_evaluation.py
```

테스트는 Gemini 비활성화, API 예외, 낮은 confidence, 불완전 응답이 첫 번째 L2로 떨어지지
않는지와, 높은 confidence만 L2로 자동 확정되는지를 검증한다. 낮은 L1 confidence로 잘못
보류된 루트가 후속 답변을 반영해 다른 L1/L2로 바뀔 수 있는지도 검증한다. 평가 계산에서는
L1/L2 abstention 분리, 독립 임계값, 80/80 분할과 81개 조합 탐색을 확인한다.

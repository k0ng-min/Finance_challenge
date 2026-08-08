# 사고유형 AI 정량평가와 안전한 Abstention

## 평가 계약

사고유형 분류는 L1 8개(`INJ/ILL/PROP/LIA/TRV/CHG/EMG/SPC`)와 각 L1 아래의 L2를
대상으로 한다. `confidence`는 정답 확률로 해석하지 않고 **자동 분류할지, 추가 질문으로
보낼지를 결정하는 라우팅 신호**로만 사용한다.

운영 안전 규칙은 다음과 같다.

1. Gemini 비활성화, 빈 입력, API 오류, 불완전한 응답에서는 임의의 L2를 선택하지 않는다.
2. L1 confidence가 `0.65` 미만이면 해당 L1 루트에 보류하고 L2 호출을 생략한다.
3. L2 confidence가 `0.70` 미만이면 해당 L1 루트에 보류한다.
4. 모델이 새 유형을 제안해도 검수 전에는 사고에 자동 할당하지 않는다.
5. L1 루트로 보류된 사고는 기존 `pending_questions` 흐름으로 넘어가 사고유형별 추가 질문을 받는다.

기본 임계값은 보수적인 초기값이다. 배포 모델이나 프롬프트가 바뀌면 아래 골드셋 평가로 다시
선정해야 한다.

## 골드셋

`backend/data/eval/incidents_gold.jsonl`에는 L1별 20건, 총 160건이 있다.

| 구분 | 건수 |
|---|---:|
| L1 8개 클래스 | 각 20 |
| easy | 70 |
| hard | 56 |
| ambiguous | 34 |
| 합계 | 160 |

각 행은 `id`, `text`, `gold_l1`, `gold_l2`, `difficulty`, `expected_abstain`을 가진다.
ambiguous 사례는 L1 맥락은 알 수 있지만 L2를 확정할 정보가 부족하므로 `gold_l2=null`,
`expected_abstain=true`로 라벨링했다. 이 파일은 개인정보가 없는 합성 평가 문장만 포함한다.

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
  --output eval/results/incident_eval.json
```

결과 JSON에는 모델명, 프롬프트 SHA-256, 평가 버전, 생성 시각, 원시 예측과 다음 지표가 기록된다.

- L1 Accuracy, Macro-F1, coverage, confusion matrix(ABSTAIN 열 포함)
- L2 end-to-end Accuracy와 Macro-F1
- L1을 맞힌 표본에 대한 L2 conditional Accuracy와 Macro-F1
- Abstention precision, recall, F1
- confidence `0.40`~`0.80` 구간의 `0.05` 단위 threshold sweep

원시 예측이 든 기존 결과를 재사용하면 API를 다시 호출하지 않고 평가 계산만 재현할 수 있다.

```bash
python -m eval.evaluate_incident_classifier \
  --predictions eval/results/incident_eval.json \
  --output eval/results/incident_eval.recomputed.json
```

## 임계값 선정과 해석

평가 도구는 각 임계값의 `abstention_f1 + l2_macro_f1_end_to_end`가 가장 큰 지점을 우선하고,
동률이면 abstention recall과 더 높은 임계값을 선택한다. 금융 안내에서는 오분류가 불필요한
담보 안내로 이어질 수 있으므로 애매한 사례를 질문으로 되돌리는 recall을 동률 기준으로 둔다.

다만 이 선택은 운영 정책의 대체물이 아니다. 모델 또는 프롬프트 변경 시 결과 JSON을 새로 남기고,
오분류 비용과 질문 증가 비용을 함께 검토한 뒤 `DEFAULT_L1_AUTO_THRESHOLD`와
`DEFAULT_L2_AUTO_THRESHOLD`를 갱신한다. 서로 다른 두 임계값을 정밀 최적화하려면 원시 예측을
기반으로 L1/L2 임계값 조합을 별도로 분석한다.

## 현재 저장된 결과

`backend/eval/results/incident_eval.validation.json`은 이 개발 환경에 Gemini 키가 없어 생성한
**골드셋 구조 검증 결과**다. `status=dataset_validated_no_live_predictions`, `metrics=null`이므로
모델 성능 결과처럼 인용하면 안 된다. 실제 Accuracy/Macro-F1 수치는 키가 설정된 평가 환경에서
위 라이브 명령을 실행해 생성한다. 수치를 꾸며 넣는 대신 미실행 상태를 명시적으로 버전 관리한다.

## 회귀 테스트

```bash
pytest -q backend/tests/test_incident_classifier_fallback.py \
  backend/tests/test_incident_classifier_evaluation.py
```

테스트는 Gemini 비활성화, API 예외, 낮은 confidence, 불완전 응답이 첫 번째 L2로 떨어지지
않는지와, 높은 confidence만 L2로 자동 확정되는지를 검증한다. 평가 계산에서는 abstention을
end-to-end 오답으로 반영하면서 precision/recall을 별도로 계산하는지도 확인한다.

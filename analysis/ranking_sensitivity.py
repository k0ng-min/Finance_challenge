"""보험사 추천 순위가 정책 계수를 조금 흔들었을 때 얼마나 버티는지 잰다.

왜 필요한가
-----------
순위를 만드는 값 중 일부는 약관에서 나온 것이 아니다. "스키를 타면 상해 무게를 0.5
올린다", "걱정된다고 고른 사고유형은 3배로 본다" 같은 것들은 우리가 정한 정책 계수다.
정답이 있는 값이 아니라는 뜻이고, 그렇다면 이 질문에 답할 수 있어야 한다.

    그 숫자가 0.5가 아니라 0.45나 0.6이었다면, 사용자가 보는 1위가 바뀌었을까?

바뀐다면 우리가 사용자에게 보여주는 것은 근거가 아니라 우리가 고른 숫자다. 그 사실을
아는 것과 모르는 것은 다르다. 이 스크립트는 답을 만들어 내지 않고 재기만 한다.

무엇을 하나
-----------
서비스가 실제로 쓰는 경로(insurer_ranking.rank_insurers → ranking_score.score_insurers)를
그대로 부른다. 계산을 여기서 다시 구현하지 않는다 — 복제본을 재면 복제본의 성질을 알게
될 뿐이다.

  1. 대표 시나리오마다 기준 순위를 낸다.
  2. 계수를 하나씩 ±10%, ±20% 흔들어(one-at-a-time) 순위를 다시 낸다.
  3. 모든 계수를 동시에 흔드는 몬테카를로도 돌린다(±20% 균등, 기본 200회).
  4. Top-1 유지율, Top-3 구성 유지율, 평균 순위 변화, Kendall tau, Spearman을 잰다.
  5. 보험사별로도 순위 변화를 따로 남긴다.

시나리오는 미리 정해 두고 결과를 보고 고르지 않는다. 결과가 나쁘게 나오는 시나리오를
빼면 이 분석은 아무 말도 하지 않는 것과 같다.

    python analysis/ranking_sensitivity.py            # 전체(몬테카를로 200회)
    python analysis/ranking_sensitivity.py --mc 50    # 빠르게

산출물
------
    analysis/data/ranking_sensitivity.csv    실행 하나당 한 줄(원자료)
    analysis/data/ranking_sensitivity.json   시나리오·계수별 집계
    docs/ranking_sensitivity.md              읽는 보고서
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import pathlib
import random
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import SessionLocal  # noqa: E402
from app.services import ranking_score  # noqa: E402
from app.services.insurer_ranking import rank_insurers  # noqa: E402

OUT_DIR = ROOT / "analysis" / "data"
DOC_PATH = ROOT / "docs" / "ranking_sensitivity.md"

#: 흔들 계수. 정수 문턱값(long_trip_days·senior_age)은 뺐다 — 8일을 7.2일로 바꾸는 건
#: 비율 섭동의 의미가 다르고(연속량이 아니라 경계), 그 경계는 따로 다뤄야 한다.
PERTURBABLE = (
    "priority_multiplier",
    "activity_bump",
    "companion_bump",
    "rental_car_bump",
    "risk_emergency_bump",
    "risk_illness_bump",
    "long_trip_bump",
    "senior_illness_bump",
    "senior_emergency_bump",
)

#: 축 비중도 정책값이다. 같이 흔든다(흔든 뒤 합이 1이 되도록 다시 정규화한다).
AXIS_CODES = ("amount", "clause", "price", "overlap", "activity")


@dataclasses.dataclass(frozen=True)
class Scenario:
    """대표 사용자 하나. 서비스가 받는 입력을 그대로 담는다."""

    key: str
    label: str
    tier: str
    plan_tier: int
    age: int
    sex: str
    trip_context: dict


#: 결과를 보기 전에 정한 시나리오들. 서로 다른 계수가 걸리도록 골랐다 —
#: 아무 계수도 안 걸리는 경우(기본 여행)부터 여러 개가 한꺼번에 걸리는 경우까지.
SCENARIOS: list[Scenario] = [
    Scenario(
        key="plain", label="아무것도 안 고른 짧은 여행(계수가 거의 안 걸림)",
        tier="균형형", plan_tier=1, age=30, sex="M",
        trip_context={"destination": "일본", "trip_days": 3, "activities": [],
                      "coverage_priority": [], "companion_type": None, "rental_car": False},
    ),
    Scenario(
        key="priority_injury", label="상해가 걱정된다고 고름(priority_multiplier만 걸림)",
        tier="균형형", plan_tier=1, age=30, sex="M",
        trip_context={"destination": "일본", "trip_days": 4, "activities": [],
                      "coverage_priority": ["INJ"], "companion_type": None, "rental_car": False},
    ),
    Scenario(
        key="ski", label="스키 여행(활동 계수)",
        tier="안정형", plan_tier=2, age=27, sex="F",
        trip_context={"destination": "일본", "trip_days": 5, "activities": ["스키"],
                      "coverage_priority": ["INJ"], "companion_type": "친구", "rental_car": False},
    ),
    Scenario(
        key="family_rentalcar", label="가족과 렌터카(동행·렌터카 계수)",
        tier="실속형", plan_tier=0, age=41, sex="M",
        trip_context={"destination": "미국", "trip_days": 7, "activities": ["렌터카"],
                      "coverage_priority": ["LIA"], "companion_type": "가족", "rental_car": True},
    ),
    Scenario(
        key="senior_long", label="고령·장기 여행(나이·기간 계수)",
        tier="최대보장형", plan_tier=2, age=68, sex="F",
        trip_context={"destination": "이탈리아", "trip_days": 21, "activities": [],
                      "coverage_priority": ["ILL"], "companion_type": "연인", "rental_car": False},
    ),
    Scenario(
        key="high_risk", label="위험지역 배낭여행(위험도·활동·기간이 함께 걸림)",
        tier="안정형", plan_tier=1, age=24, sex="M",
        trip_context={"destination": "필리핀", "trip_days": 14, "risk_level": "높음",
                      "activities": ["스쿠버다이빙", "오토바이"], "coverage_priority": ["INJ", "EMG"],
                      "companion_type": "친구", "rental_car": False},
    ),
    Scenario(
        key="claim_simple", label="청구 편의 우선(축 비중이 다른 기준)",
        tier="간편청구형", plan_tier=1, age=35, sex="F",
        trip_context={"destination": "베트남", "trip_days": 6, "activities": ["수영"],
                      "coverage_priority": ["PROP"], "companion_type": "가족", "rental_car": False},
    ),
    Scenario(
        key="everything", label="고를 수 있는 걸 다 고른 경우(계수가 전부 걸림)",
        tier="균형형", plan_tier=1, age=63, sex="M",
        trip_context={"destination": "네팔", "trip_days": 15, "risk_level": "매우높음",
                      "activities": ["등산", "트래킹", "렌터카"],
                      "coverage_priority": ["INJ", "ILL", "EMG"],
                      "companion_type": "반려동물 동반", "rental_car": True},
    ),
]


# --- 순위 계산 --------------------------------------------------------------

def score_for(db, scenario: Scenario, *, heuristics, axis_override):
    """서비스와 같은 경로로 (보험사코드, 총점) 목록을 낸다."""
    base = rank_insurers(db, scenario.tier, scenario.trip_context)
    scored = ranking_score.score_insurers(
        db,
        tier_code=scenario.tier,
        plan_tier=scenario.plan_tier,
        trip_context=scenario.trip_context,
        ranking=base,
        age=scenario.age,
        sex=scenario.sex,
        external_policies=None,
        heuristics=heuristics,
        axis_weights_override=axis_override,
    )
    return [(row.insurer_code, row.total) for row in scored]


def rank_for(db, scenario: Scenario, *, heuristics, axis_override) -> list[str]:
    """위와 같되 보험사 코드만 순서대로."""
    return [code for code, _ in score_for(db, scenario, heuristics=heuristics,
                                          axis_override=axis_override)]


# --- 지표 -------------------------------------------------------------------

def kendall_tau(a: list[str], b: list[str]) -> float | None:
    """두 순위의 Kendall tau-b. 같은 항목 집합일 때만 뜻이 있다.

    scipy를 쓰지 않는다 — 이 저장소는 분석 하나 때문에 무거운 의존성을 들이지 않는다.
    항목이 열 개 미만이라 O(n^2)로 세도 순식간이다."""
    if sorted(a) != sorted(b) or len(a) < 2:
        return None
    rank_a = {code: i for i, code in enumerate(a)}
    rank_b = {code: i for i, code in enumerate(b)}
    concordant = discordant = 0
    codes = list(a)
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            x, y = codes[i], codes[j]
            sign = (rank_a[x] - rank_a[y]) * (rank_b[x] - rank_b[y])
            if sign > 0:
                concordant += 1
            elif sign < 0:
                discordant += 1
    total = concordant + discordant
    return (concordant - discordant) / total if total else None


def spearman(a: list[str], b: list[str]) -> float | None:
    """순위 상관(동점 없음 — 순위가 곧 서로 다른 정수다)."""
    if sorted(a) != sorted(b) or len(a) < 2:
        return None
    rank_a = {code: i for i, code in enumerate(a)}
    rank_b = {code: i for i, code in enumerate(b)}
    n = len(a)
    d2 = sum((rank_a[c] - rank_b[c]) ** 2 for c in a)
    return 1 - (6 * d2) / (n * (n * n - 1))


def compare(base: list[str], moved: list[str]) -> dict:
    """기준 순위와 흔든 순위를 견준다."""
    rank_base = {code: i for i, code in enumerate(base)}
    rank_moved = {code: i for i, code in enumerate(moved)}
    shared = [c for c in base if c in rank_moved]
    changes = {c: rank_moved[c] - rank_base[c] for c in shared}
    return {
        "top1_kept": bool(base and moved and base[0] == moved[0]),
        "top3_set_kept": set(base[:3]) == set(moved[:3]),
        "top3_order_kept": base[:3] == moved[:3],
        "mean_abs_rank_change": (
            statistics.fmean(abs(v) for v in changes.values()) if changes else 0.0
        ),
        "max_abs_rank_change": max((abs(v) for v in changes.values()), default=0),
        "kendall_tau": kendall_tau(base, moved),
        "spearman": spearman(base, moved),
        "per_insurer_change": changes,
    }


# --- 섭동 -------------------------------------------------------------------

def scaled(heuristics, field: str, factor: float):
    """계수 하나만 배율만큼 바꾼 사본."""
    current = getattr(heuristics, field)
    if current is None:  # priority_multiplier는 None이면 설정파일 값을 쓴다
        current = float(ranking_score.load_weights().get("priority_multiplier", 3.0))
    return dataclasses.replace(heuristics, **{field: current * factor})


def renormalized(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()} if total > 0 else dict(weights)


def base_axis_weights(tier: str) -> dict[str, float]:
    config = ranking_score.load_weights()
    return dict(
        (config.get("axis_weights") or {}).get(tier)
        or ranking_score._default_axis_weights()
    )


def run(mc_runs: int, seed: int) -> dict:
    db = SessionLocal()
    rows: list[dict] = []
    summary: dict = {"scenarios": {}, "by_factor": {}, "monte_carlo": {}, "per_insurer": {}}
    rng = random.Random(seed)

    resolved = dataclasses.replace(
        ranking_score.DEFAULT_HEURISTICS,
        priority_multiplier=float(ranking_score.load_weights().get("priority_multiplier", 3.0)),
    )

    try:
        for scenario in SCENARIOS:
            axis_base = base_axis_weights(scenario.tier)
            baseline_scores = score_for(db, scenario, heuristics=resolved, axis_override=axis_base)
            base = [code for code, _ in baseline_scores]
            # 1위와 2위의 총점 격차. 아래에서 드러나지만, 순위가 흔들리는 정도는 어떤
            # 계수를 흔들었는가보다 이 격차에 훨씬 크게 매여 있다.
            margin = (
                baseline_scores[0][1] - baseline_scores[1][1]
                if len(baseline_scores) >= 2 else None
            )
            summary["scenarios"][scenario.key] = {
                "label": scenario.label, "tier": scenario.tier,
                "plan_tier": scenario.plan_tier, "baseline": base,
                "baseline_totals": {c: round(t, 3) for c, t in baseline_scores},
                "top2_margin": round(margin, 3) if margin is not None else None,
            }
            if len(base) < 2:
                continue

            # (1) 계수 하나씩 ±10%, ±20%
            for field in PERTURBABLE:
                for factor in (0.8, 0.9, 1.1, 1.2):
                    moved = rank_for(
                        db, scenario,
                        heuristics=scaled(resolved, field, factor),
                        axis_override=axis_base,
                    )
                    rows.append({
                        "scenario": scenario.key, "kind": "oat_heuristic",
                        "param": field, "factor": factor, "run": 0,
                        "ranking": "|".join(moved), **_flat(compare(base, moved)),
                    })

            # (2) 축 비중 하나씩 ±10%, ±20% (흔든 뒤 합을 1로 되돌린다)
            for axis in AXIS_CODES:
                if axis not in axis_base:
                    continue
                for factor in (0.8, 0.9, 1.1, 1.2):
                    tweaked = dict(axis_base)
                    tweaked[axis] = tweaked[axis] * factor
                    moved = rank_for(
                        db, scenario, heuristics=resolved,
                        axis_override=renormalized(tweaked),
                    )
                    rows.append({
                        "scenario": scenario.key, "kind": "oat_axis",
                        "param": f"axis:{axis}", "factor": factor, "run": 0,
                        "ranking": "|".join(moved), **_flat(compare(base, moved)),
                    })

            # (3) 몬테카를로 — 모든 계수와 축 비중을 한꺼번에 ±20% 안에서 흔든다.
            for run_index in range(mc_runs):
                jitter = {
                    f: getattr(resolved, f) * rng.uniform(0.8, 1.2) for f in PERTURBABLE
                }
                tweaked_axis = renormalized({
                    a: w * rng.uniform(0.8, 1.2) for a, w in axis_base.items()
                })
                moved = rank_for(
                    db, scenario,
                    heuristics=dataclasses.replace(resolved, **jitter),
                    axis_override=tweaked_axis,
                )
                rows.append({
                    "scenario": scenario.key, "kind": "monte_carlo",
                    "param": "all", "factor": 0.0, "run": run_index,
                    "ranking": "|".join(moved), **_flat(compare(base, moved)),
                })
    finally:
        db.close()

    _summarize(rows, summary)
    return {"rows": rows, "summary": summary}


def _flat(result: dict) -> dict:
    per = result.pop("per_insurer_change")
    out = dict(result)
    out["per_insurer_change"] = json.dumps(per, ensure_ascii=False)
    return out


def _agg(subset: list[dict]) -> dict:
    if not subset:
        return {}
    taus = [r["kendall_tau"] for r in subset if r["kendall_tau"] is not None]
    rhos = [r["spearman"] for r in subset if r["spearman"] is not None]
    return {
        "runs": len(subset),
        "top1_kept_rate": statistics.fmean(1.0 if r["top1_kept"] else 0.0 for r in subset),
        "top3_set_kept_rate": statistics.fmean(1.0 if r["top3_set_kept"] else 0.0 for r in subset),
        "top3_order_kept_rate": statistics.fmean(1.0 if r["top3_order_kept"] else 0.0 for r in subset),
        "mean_abs_rank_change": statistics.fmean(r["mean_abs_rank_change"] for r in subset),
        "max_abs_rank_change": max(r["max_abs_rank_change"] for r in subset),
        "kendall_tau_mean": statistics.fmean(taus) if taus else None,
        "kendall_tau_min": min(taus) if taus else None,
        "spearman_mean": statistics.fmean(rhos) if rhos else None,
        "spearman_min": min(rhos) if rhos else None,
    }


def _summarize(rows: list[dict], summary: dict) -> None:
    summary["overall"] = _agg(rows)
    summary["by_kind"] = {
        kind: _agg([r for r in rows if r["kind"] == kind])
        for kind in ("oat_heuristic", "oat_axis", "monte_carlo")
    }
    params = sorted({r["param"] for r in rows if r["kind"] != "monte_carlo"})
    summary["by_factor"] = {p: _agg([r for r in rows if r["param"] == p]) for p in params}
    for key in summary["scenarios"]:
        subset = [r for r in rows if r["scenario"] == key]
        summary["scenarios"][key]["metrics"] = _agg(subset)
        summary["scenarios"][key]["monte_carlo"] = _agg(
            [r for r in subset if r["kind"] == "monte_carlo"]
        )

    # 보험사별: 순위가 얼마나 움직였나.
    moves: dict[str, list[int]] = {}
    for r in rows:
        for code, delta in json.loads(r["per_insurer_change"]).items():
            moves.setdefault(code, []).append(delta)
    summary["per_insurer"] = {
        code: {
            "observations": len(vals),
            "mean_abs_change": statistics.fmean(abs(v) for v in vals),
            "max_abs_change": max(abs(v) for v in vals),
            "moved_at_all_rate": statistics.fmean(1.0 if v else 0.0 for v in vals),
        }
        for code, vals in sorted(moves.items())
    }


# --- 출력 -------------------------------------------------------------------

def write_outputs(result: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = result["rows"]
    fields = list(rows[0].keys()) if rows else []
    with (OUT_DIR / "ranking_sensitivity.csv").open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (OUT_DIR / "ranking_sensitivity.json").write_text(
        json.dumps(result["summary"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    DOC_PATH.write_text(render_report(result["summary"]), encoding="utf-8")


def _pct(x) -> str:
    return "—" if x is None else f"{x * 100:.1f}%"


def _num(x, digits=3) -> str:
    return "—" if x is None else f"{x:.{digits}f}"


def render_report(s: dict) -> str:
    overall = s["overall"]
    by_kind = s["by_kind"]
    lines: list[str] = []
    add = lines.append

    add("# 추천 순위는 정책 계수를 흔들면 얼마나 흔들리나")
    add("")
    add("`analysis/ranking_sensitivity.py`가 만든 문서다. 손으로 고치지 말고 스크립트를 다시 돌릴 것.")
    add("")
    add("## 왜 쟀나")
    add("")
    add("순위를 만드는 값 중 일부는 약관에서 나온 것이 아니다. \"스키를 타면 상해 무게를 0.5")
    add("올린다\", \"걱정된다고 고른 사고유형은 3배로 본다\" 같은 것은 우리가 정한 정책 계수다.")
    add("정답이 있는 값이 아니니, 그 숫자가 조금 달랐다면 사용자가 보는 1위가 바뀌었을지를")
    add("알아야 한다. 바뀐다면 우리가 보여주는 건 근거가 아니라 우리가 고른 숫자다.")
    add("")
    add("## 어떻게 쟀나")
    add("")
    add(f"- 대표 시나리오 {len(s['scenarios'])}개. 결과를 보기 전에 정했고, 하나도 빼지 않았다.")
    add("- 서비스가 실제로 쓰는 경로(`rank_insurers` → `score_insurers`)를 그대로 부른다.")
    add("- **OAT(한 번에 하나)**: 계수와 축 비중을 하나씩 ±10%, ±20%.")
    add(f"- **몬테카를로**: 모든 계수와 축 비중을 한꺼번에 ±20% 균등분포로 흔들기, "
        f"시나리오당 {by_kind['monte_carlo'].get('runs', 0) // max(len(s['scenarios']), 1)}회.")
    add("- 축 비중은 흔든 뒤 합이 1이 되도록 다시 정규화한다(그래야 총점 척도가 유지된다).")
    add("- 정수 문턱값(장기여행 8일, 고령 60세)은 비율로 흔들지 않았다 — 연속량이 아니라 경계라")
    add("  ±10%의 뜻이 다르다. 이건 아직 안 잰 영역이다.")
    add("")
    add("## 전체 결과")
    add("")
    add(f"실행 {overall['runs']}회.")
    add("")
    add("| 구분 | 실행 | Top-1 유지 | Top-3 구성 유지 | Top-3 순서 유지 | 평균 순위변화 | 최대 | Kendall τ 평균 | τ 최소 | Spearman 평균 |")
    add("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for label, key in [("계수 OAT", "oat_heuristic"), ("축 비중 OAT", "oat_axis"), ("몬테카를로", "monte_carlo")]:
        a = by_kind.get(key) or {}
        if not a:
            continue
        add(f"| {label} | {a['runs']} | {_pct(a['top1_kept_rate'])} | {_pct(a['top3_set_kept_rate'])} "
            f"| {_pct(a['top3_order_kept_rate'])} | {_num(a['mean_abs_rank_change'], 2)} "
            f"| {a['max_abs_rank_change']} | {_num(a['kendall_tau_mean'])} | {_num(a['kendall_tau_min'])} "
            f"| {_num(a['spearman_mean'])} |")
    add("")

    # 불안정한 자리를 먼저 말한다. 표 안에 묻어 두면 못 보고 지나간다.
    shaky = [
        (key, info) for key, info in s["scenarios"].items()
        if (info.get("metrics") or {}).get("top1_kept_rate", 1.0) < 0.95
    ]
    add("## 주의 — 순위가 흔들리는 자리")
    add("")
    if not shaky:
        add("Top-1 유지율이 95% 아래로 내려간 시나리오는 없었다.")
    else:
        add("아래 시나리오에서는 계수를 ±20% 안에서 흔드는 것만으로 1위가 바뀌었다.")
        add("여기서 1위는 근거가 아니라 우리가 고른 숫자에 기대고 있다는 뜻이다.")
        add("")
        for key, info in shaky:
            m = info["metrics"]
            margin = info.get("top2_margin")
            totals = info.get("baseline_totals") or {}
            top2 = list(totals.items())[:2]
            add(f"- **{info['label']}** (`{key}`) — Top-1 유지 {_pct(m['top1_kept_rate'])}, "
                f"Kendall τ 최소 {_num(m['kendall_tau_min'])}")
            if len(top2) == 2:
                add(f"  - 기준 1·2위: {top2[0][0]} {top2[0][1]:.2f}점 vs "
                    f"{top2[1][0]} {top2[1][1]:.2f}점 — 격차 **{margin:.2f}점**")
        add("")
        add("공통점은 계수의 종류가 아니라 **1·2위 총점 격차**다. 격차가 0.1점 안쪽이면 어떤")
        add("계수를 건드려도 순위가 뒤집히고, 3점 넘게 벌어져 있으면 무엇을 흔들어도 그대로다.")
        add("바꿔 말하면 이건 계수가 잘못됐다는 신호가 아니라, **그 시나리오에서는 두 보험사가")
        add("실제로 우열을 가리기 어렵다**는 사실이 순위 한 줄로 뭉개져 보이는 것에 가깝다.")
        add("")

    add("## 시나리오별")
    add("")
    add("| 시나리오 | 기준 1위 | 1·2위 격차 | Top-1 유지 | Top-3 구성 유지 | 평균 순위변화 | Kendall τ 최소 |")
    add("|---|---|---:|---:|---:|---:|---:|")
    for key, info in s["scenarios"].items():
        m = info.get("metrics") or {}
        if not m:
            continue
        top = info["baseline"][0] if info["baseline"] else "—"
        margin = info.get("top2_margin")
        add(f"| {info['label']} | {top} | {_num(margin, 2)} | {_pct(m['top1_kept_rate'])} "
            f"| {_pct(m['top3_set_kept_rate'])} | {_num(m['mean_abs_rank_change'], 2)} "
            f"| {_num(m['kendall_tau_min'])} |")
    add("")

    add("## 어느 계수가 가장 민감한가")
    add("")
    add("Top-1 유지율이 낮을수록 그 계수를 흔들었을 때 1위가 잘 바뀐다는 뜻이다.")
    add("")
    add("| 계수 | 실행 | Top-1 유지 | Top-3 구성 유지 | 평균 순위변화 | Kendall τ 최소 |")
    add("|---|---:|---:|---:|---:|---:|")
    ranked = sorted(
        ((p, a) for p, a in s["by_factor"].items() if a),
        key=lambda kv: (kv[1]["top1_kept_rate"], -kv[1]["mean_abs_rank_change"]),
    )
    for param, a in ranked:
        add(f"| `{param}` | {a['runs']} | {_pct(a['top1_kept_rate'])} | {_pct(a['top3_set_kept_rate'])} "
            f"| {_num(a['mean_abs_rank_change'], 2)} | {_num(a['kendall_tau_min'])} |")
    add("")

    add("## 보험사별")
    add("")
    add("| 보험사 | 관측 | 순위가 움직인 비율 | 평균 |순위변화| | 최대 |")
    add("|---|---:|---:|---:|---:|")
    for code, a in sorted(s["per_insurer"].items(), key=lambda kv: -kv[1]["mean_abs_change"]):
        add(f"| {code} | {a['observations']} | {_pct(a['moved_at_all_rate'])} "
            f"| {_num(a['mean_abs_change'], 2)} | {a['max_abs_change']} |")
    add("")

    add("## 읽는 법과 한계")
    add("")
    add("- Top-1 유지율이 100%가 아니면, 그 시나리오에서 1위는 계수 선택에 기대고 있다는 뜻이다.")
    add("  낮게 나온 자리를 숨기지 않는다 — 위 표에 그대로 있다.")
    add("- Kendall τ는 순서쌍이 얼마나 보존됐는지다. 1.0이면 순서가 그대로고, 낮을수록 뒤섞였다.")
    add("- 이 분석은 **계수만** 흔든다. 약관 근거 축의 단계, 보장금액, 보험료 같은 자료 자체는")
    add("  그대로 뒀다. 자료가 틀렸을 때 순위가 어떻게 되는지는 여기서 답하지 않는다.")
    add("- 정수 문턱값(8일·60세)과 `ACTIVITY_TO_INCIDENT` 같은 매핑표는 흔들지 않았다.")
    add("- 기존보험(overlap 축)은 등록하지 않은 상태로 뒀다. 등록 시에는 축이 중립값 또는")
    add("  근거 기반 점수로 바뀌므로 별도 분석이 필요하다.")
    add("")
    return "\n".join(lines) + "\n"


def main() -> None:
    # 윈도우 콘솔 기본 인코딩(cp949)은 τ나 — 같은 글자를 못 찍는다. 산출물은 전부
    # UTF-8 파일로 나가므로 화면 출력만 맞춰 준다.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mc", type=int, default=200, help="시나리오당 몬테카를로 실행 수")
    parser.add_argument("--seed", type=int, default=20260904, help="난수 시드(재현용)")
    args = parser.parse_args()

    result = run(args.mc, args.seed)
    write_outputs(result)

    o = result["summary"]["overall"]
    print(f"실행 {o['runs']}회 — Top-1 유지 {_pct(o['top1_kept_rate'])}, "
          f"Top-3 구성 유지 {_pct(o['top3_set_kept_rate'])}, "
          f"Kendall τ 평균 {_num(o['kendall_tau_mean'])}")
    print(f"  {OUT_DIR / 'ranking_sensitivity.csv'}")
    print(f"  {OUT_DIR / 'ranking_sensitivity.json'}")
    print(f"  {DOC_PATH}")


if __name__ == "__main__":
    main()

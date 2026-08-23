# 보험사 순위 가중치·정규화 계수 산출
#
# 입력  : analysis/data/coverage_amounts.csv, analysis/data/premiums.csv
#         (analysis/export_ranking_inputs.py가 KB에서 뽑아 둔다)
# 출력  : backend/app/data/ranking_weights.json  ← 저장소에 커밋한다
#
# 실행  : Rscript analysis/ranking_weights.R
#
# 이 스크립트는 서버 실행 경로에 있지 않다. 여기서 만든 계수를 JSON으로 떨어뜨려
# 커밋하고, 서버는 그 파일만 읽는다. 계수를 다시 뽑고 싶을 때만 돌리면 된다.

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(readr)
  library(jsonlite)
})

# 저장소 루트 찾기 — 어느 디렉터리에서 돌리든 같은 파일을 읽고 쓰게 한다.
find_root <- function(start = normalizePath(".", mustWork = TRUE)) {
  dir <- start
  repeat {
    if (dir.exists(file.path(dir, "analysis")) && dir.exists(file.path(dir, "backend"))) return(dir)
    parent <- dirname(dir)
    if (parent == dir) stop("저장소 루트를 찾지 못했습니다. 저장소 안에서 실행해 주세요.")
    dir <- parent
  }
}
root <- find_root()

in_dir <- file.path(root, "analysis", "data")
out_path <- file.path(root, "backend", "app", "data", "ranking_weights.json")

amounts <- read_csv(file.path(in_dir, "coverage_amounts.csv"), show_col_types = FALSE)
premiums <- read_csv(file.path(in_dir, "premiums.csv"), show_col_types = FALSE)

# ---------------------------------------------------------------------------
# 1. 보장항목 → 사고유형 매핑
#
# 21개 항목을 8개 대분류에 붙인다. 한 항목이 두 유형에 걸치면(비급여 의료비처럼 상해와
# 질병 모두에 쓰인다) 절반씩 나눈다. 근거 없이 갖다 붙이지 않는다 — 어느 유형에도
# 해당하지 않으면 표에 넣지 않고, 그 항목은 A축 계산에서 빠진다.
# ---------------------------------------------------------------------------
metric_map <- tribble(
  ~metric_label,              ~incident, ~share,
  "상해사망보험금",              "INJ",  1.0,
  "상해후유장해보험금",           "INJ",  1.0,
  "해외 상해의료비",             "INJ",  1.0,
  "국내 상해의료비(급여)",        "INJ",  1.0,
  "상해입원일당",                "INJ",  1.0,
  "질병사망/고도후유장해",        "ILL",  1.0,
  "해외 질병의료비",             "ILL",  1.0,
  "국내 질병의료비(급여)",        "ILL",  1.0,
  "식중독 보상",                "ILL",  1.0,
  "특정전염병 보상금",           "ILL",  1.0,
  "국내 3대 비급여의료비",        "INJ",  0.5,
  "국내 3대 비급여의료비",        "ILL",  0.5,
  "국내 비급여 MRI/MRA",         "INJ",  0.5,
  "국내 비급여 MRI/MRA",         "ILL",  0.5,
  "휴대품손해(분실제외)",         "PROP", 1.0,
  "자택도난손해",                "PROP", 1.0,
  "여권분실 재발급비용",          "PROP", 1.0,
  "배상책임",                   "LIA",  1.0,
  "수하물/항공편 지연",          "TRV",  1.0,
  "출국항공기지연(지수형)",       "TRV",  1.0,
  "항공기납치위로금",            "TRV",  1.0,
  "여행중단 추가비용",           "CHG",  1.0,
  "중대사고 구조송환비용",        "EMG",  1.0
)

mapped <- unique(metric_map$metric_label)
unmapped <- setdiff(unique(amounts$metric_label), mapped)
if (length(unmapped) > 0) {
  message("사고유형에 안 붙은 항목(A축에서 빠짐): ", paste(unmapped, collapse = ", "))
}

# ---------------------------------------------------------------------------
# 2. 항목별 정규화 구간과 "등급 변별력"
#
# 정규화는 항목마다 6개사 × 3등급 = 18개 값을 한 묶음으로 놓고 한다. 등급 안에서만
# 정규화하면 등급을 올려도 안 변하는 항목까지 등급마다 다시 펴져서, 실제로는 차이가
# 없는데 순서가 흔들린다.
#
# tier_spread는 "이 항목이 등급을 실제로 가르는가"를 잰다. 보험사마다 (그 보험사의
# 최고등급 금액 - 최저등급 금액)을 전체 최댓값으로 나눠 평균한 값이다. DB 해외상해의료비처럼
# 세 등급이 모두 같으면 0, 카카오페이처럼 3000→10000으로 뛰면 크다.
# ---------------------------------------------------------------------------
metric_stats <- amounts %>%
  filter(metric_label %in% mapped) %>%
  group_by(metric_label) %>%
  mutate(overall_max = max(amount)) %>%
  group_by(metric_label, insurer_code) %>%
  summarise(within_insurer_spread = (max(amount) - min(amount)) / max(first(overall_max), 1),
            .groups = "drop") %>%
  group_by(metric_label) %>%
  summarise(tier_spread = mean(within_insurer_spread), .groups = "drop")

metric_norm <- amounts %>%
  filter(metric_label %in% mapped) %>%
  group_by(metric_label) %>%
  summarise(min = min(amount), max = max(amount), n = n(), .groups = "drop") %>%
  left_join(metric_stats, by = "metric_label")

cat("\n== 항목별 등급 변별력(tier_spread) 상위 ==\n")
print(metric_norm %>% arrange(desc(tier_spread)) %>% select(metric_label, min, max, tier_spread), n = 25)

# ---------------------------------------------------------------------------
# 3. 보험료 정규화 구간
#
# 보험료는 1일 기준으로 환산해서 비교한다(조회값의 period_days가 보험사마다 다르다).
# 나이·성별에 따라 값이 크게 달라지므로 구간은 나이대별로 따로 잡는다 — 20대 요율로
# 60대를 재면 모든 보험사가 나란히 비싸 보여서 가격 축이 순위를 못 가른다.
# ---------------------------------------------------------------------------
premium_norm <- premiums %>%
  mutate(daily = premium / pmax(period_days, 1),
         age_band = pmin(floor(age / 10) * 10, 70)) %>%
  group_by(age_band) %>%
  summarise(min = min(daily), max = max(daily), n = n(), .groups = "drop")

cat("\n== 나이대별 1일 보험료 구간 ==\n")
print(premium_norm)

priced_insurers <- sort(unique(premiums$insurer_code))
cat("\n보험료 자료가 있는 보험사:", paste(priced_insurers, collapse = ", "), "\n")

# ---------------------------------------------------------------------------
# 4. 축 비중
#
# 다섯 축(보장금액·약관근거·가격·기존보험보완·활동대응)을 비교 기준마다 다르게 섞는다.
# 기존 네 축 비중(insurer_ranking.py TIERS)을 "약관근거" 하나로 접고, 나머지를 새 축에
# 나눠 준다. 비중 자체는 판단이지만, 아래 두 가지는 자료에서 나온 제약을 따른다.
#   - 보장금액 축이 가장 크다. 등급을 가르는 정보가 여기에만 있다(tier_spread 참고).
#   - 가격 축은 자료가 4개사뿐이라 과하게 주지 않는다. 자료가 없는 보험사는 이 축을
#     빼고 나머지로 다시 100%를 맞추므로, 비중이 크면 그 보정의 영향도 커진다.
# ---------------------------------------------------------------------------
axis_weights <- list(
  "안정형"     = list(amount = 0.34, clause = 0.32, price = 0.10, overlap = 0.14, activity = 0.10),
  "실속형"     = list(amount = 0.30, clause = 0.24, price = 0.26, overlap = 0.12, activity = 0.08),
  "최대보장형" = list(amount = 0.46, clause = 0.28, price = 0.04, overlap = 0.14, activity = 0.08),
  "간편청구형" = list(amount = 0.26, clause = 0.40, price = 0.12, overlap = 0.12, activity = 0.10),
  "균형형"     = list(amount = 0.34, clause = 0.28, price = 0.16, overlap = 0.12, activity = 0.10)
)

stopifnot(all(abs(sapply(axis_weights, function(w) sum(unlist(w))) - 1) < 1e-9))

# ---------------------------------------------------------------------------
# 5. 산출물
# ---------------------------------------------------------------------------
metric_to_incident <- metric_map %>%
  group_by(metric_label) %>%
  summarise(shares = list(setNames(as.list(share), incident)), .groups = "drop")

out <- list(
  generated_at = format(Sys.time(), "%Y-%m-%d"),
  generated_by = "analysis/ranking_weights.R",
  source_rows = list(coverage = nrow(amounts), premium = nrow(premiums)),
  # 사용자가 "걱정되는 사고유형"으로 고른 유형의 보장금액 항목에 곱하는 배수.
  priority_multiplier = 3.0,
  priced_insurers = priced_insurers,
  axis_weights = axis_weights,
  metric_to_incident = setNames(metric_to_incident$shares, metric_to_incident$metric_label),
  metric_norm = setNames(
    lapply(seq_len(nrow(metric_norm)), function(i) {
      list(min = metric_norm$min[i], max = metric_norm$max[i],
           tier_spread = round(metric_norm$tier_spread[i], 4))
    }),
    metric_norm$metric_label
  ),
  premium_norm = setNames(
    lapply(seq_len(nrow(premium_norm)), function(i) {
      list(min = premium_norm$min[i], max = premium_norm$max[i])
    }),
    as.character(premium_norm$age_band)
  )
)

dir.create(dirname(out_path), recursive = TRUE, showWarnings = FALSE)
write(toJSON(out, auto_unbox = TRUE, pretty = TRUE, digits = 6), out_path)
cat("\n", out_path, " 에 계수를 썼습니다.\n", sep = "")

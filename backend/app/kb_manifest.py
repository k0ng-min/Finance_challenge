"""KB를 일부러 고친 뒤 dataset_manifest.json을 실제 DB에 다시 맞춘다.

매니페스트는 "커밋된 app.db가 무엇을 담고 있어야 하는가"를 적어 둔 기록이고,
scripts/validate_kb.py가 그것과 실제 DB를 대조해 KB가 아무도 모르게 바뀌는 걸 잡는다.
그 검사는 KB를 일부러 고쳤을 때도 똑같이 걸리는데, 이건 정상이다 — "이번 변경은 의도한
것"이라고 기록에 반영해야 통과한다.

손으로 고치면 보험사 다섯 개 × 숫자 다섯 개를 옮겨 적다가 하나만 틀려도 검사만 통과하고
기록은 어긋난 상태가 된다. 그래서 갱신은 DB에서 직접 세어 쓴다.

**개수와 지문만 다시 쓴다.** 출처 URL·PDF 해시·검증 상태·known_gap처럼 사람이 원본을
확인해 적어 넣은 값은 손대지 않는다 — 그건 세어서 알 수 있는 값이 아니라 근거를 확인한
기록이고, 자동으로 덮어쓰면 확인하지 않은 것이 확인된 것처럼 보이게 된다.

쓰는 법::

    cd backend
    python -m app.kb_manifest            # 무엇이 달라지는지만 확인
    python -m app.kb_manifest --confirm  # 실제로 다시 쓴다
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from scripts.validate_kb import (
    DEFAULT_DATABASE, DEFAULT_MANIFEST, build_coverage_matrix, compute_kb_fingerprint,
)

# DB에서 세어 다시 쓰는 값. 나머지 필드는 사람이 확인해 적은 것이라 그대로 둔다.
COUNTED_FIELDS = ("coverage_count", "clause_count", "incident_map_count", "term_count", "doc_map_count")


def plan_refresh(database: Path | str = DEFAULT_DATABASE,
                 manifest_path: Path | str = DEFAULT_MANIFEST) -> tuple[dict, list[str]]:
    """갱신된 매니페스트 내용과, 무엇이 달라지는지 사람이 읽을 수 있는 목록을 돌려준다."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    changes: list[str] = []

    connection = sqlite3.connect(Path(database))
    try:
        connection.row_factory = sqlite3.Row
        matrix = {row["insurer"]: row for row in build_coverage_matrix(connection)}
        fingerprint = compute_kb_fingerprint(connection)
    finally:
        connection.close()

    for source in manifest.get("sources", []):
        code = source.get("insurer")
        counted = matrix.get(code)
        if counted is None:
            changes.append(f"{code}: DB에 없는 보험사라 개수를 갱신하지 않았다")
            continue
        for field in COUNTED_FIELDS:
            before, after = source.get(field), counted.get(field)
            if before != after:
                changes.append(f"{code}.{field}: {before} → {after}")
                source[field] = after

    if manifest.get("kb_content_sha256") != fingerprint:
        changes.append(f"kb_content_sha256: {manifest.get('kb_content_sha256')} → {fingerprint}")
        manifest["kb_content_sha256"] = fingerprint

    return manifest, changes


def refresh_manifest(database: Path | str = DEFAULT_DATABASE,
                     manifest_path: Path | str = DEFAULT_MANIFEST) -> list[str]:
    """매니페스트를 실제 DB에 맞춰 다시 쓴다. 달라진 항목 목록을 돌려준다."""
    manifest, changes = plan_refresh(database, manifest_path)
    if changes:
        Path(manifest_path).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    return changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--confirm", action="store_true", help="실제로 다시 쓴다(없으면 미리보기)")
    args = parser.parse_args(argv)

    _, changes = plan_refresh(args.database, args.manifest)
    if not changes:
        print("매니페스트가 이미 DB와 맞는다 — 고칠 것이 없다.")
        return 0
    for line in changes:
        print(f"  {line}")
    if args.confirm:
        refresh_manifest(args.database, args.manifest)
        print(f"매니페스트 {len(changes)}건 갱신 완료.")
    else:
        print("--confirm 없이 실행했으므로 아무것도 쓰지 않았다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import { useEffect, useState } from "react";

/** 목록/표가 길어져도 스크롤을 내리는 대신 "다음"을 눌러 다음 장으로 넘기게 한다.
 * pageSize개씩 잘라서 보여주고, 목록 자체가 바뀌면(다른 사고 선택 등) 1페이지로 되돌린다. */
export function usePager<T>(items: T[], pageSize: number) {
  const [page, setPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const clampedPage = Math.min(page, totalPages - 1);

  useEffect(() => {
    setPage(0);
  }, [items.length]);

  const pageItems = items.slice(clampedPage * pageSize, clampedPage * pageSize + pageSize);
  return { page: clampedPage, setPage, totalPages, pageItems };
}

export function PagerNav({
  page, totalPages, onChange, label = "쪽",
}: {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
  label?: string;
}) {
  if (totalPages <= 1) return null;
  return (
    <div className="pager-nav">
      <button
        type="button"
        className="pager-navbtn"
        onClick={() => onChange(Math.max(0, page - 1))}
        disabled={page === 0}
      >
        ← 이전
      </button>
      <span className="pager-count">{page + 1} / {totalPages} {label}</span>
      <button
        type="button"
        className="pager-navbtn"
        onClick={() => onChange(Math.min(totalPages - 1, page + 1))}
        disabled={page === totalPages - 1}
      >
        다음 →
      </button>
    </div>
  );
}

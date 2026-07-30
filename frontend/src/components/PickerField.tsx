import { useState } from "react";
import { Modal } from "./Modal";

export interface PickerOption {
  value: string;
  label: string;
}

/** 네이티브 <select>는 닫힌 상자만 스타일링할 수 있고 펼쳐진 옵션 목록은 브라우저가
 * 그려서 앱 톤에 맞출 수 없다. 그래서 옵션 목록도 우리 모달로 직접 그리는 대체 컴포넌트. */
export function PickerField({
  value, options, placeholder = "선택하세요", modalTitle, onChange, disabled,
}: {
  value: string;
  options: PickerOption[];
  placeholder?: string;
  modalTitle?: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const current = options.find((o) => o.value === value);
  return (
    <>
      <button
        type="button"
        className="picker-field"
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        <span className={current ? "picker-field__value" : "picker-field__value picker-field__value--placeholder"}>
          {current ? current.label : placeholder}
        </span>
        <span className="picker-field__chevron" aria-hidden>⌄</span>
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title={modalTitle ?? placeholder}>
        <div className="picker-list">
          {options.map((o) => (
            <button
              key={o.value}
              type="button"
              className={`picker-list__item${o.value === value ? " picker-list__item--active" : ""}`}
              onClick={() => { onChange(o.value); setOpen(false); }}
            >
              {o.label}
              {o.value === value && <span className="picker-list__check">✓</span>}
            </button>
          ))}
        </div>
      </Modal>
    </>
  );
}

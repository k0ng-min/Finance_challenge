/**
 * 서류 사진을 외부 AI로 보내기 전에 그 사실을 알리는지 지킨다.
 *
 * 예전 화면은 결과를 다 보여준 뒤에야 "올린 사진과 번역 내용은 저장하지 않아요"라고
 * 말했다. 그건 맞는 말이지만 사용자가 알아야 할 것의 절반이다 — 우리 서버에 저장하지
 * 않는 것과, 사진이 Google Gemini API로 전송되지 않는 것은 다른 이야기다. 그리고
 * 사진은 실제로 전송된다. 게다가 그 안내는 이미 보낸 뒤에 나왔다.
 *
 * 그래서 고지를 파일 선택기 앞에 세웠다. 여기서 지키는 것:
 *
 *   1. 고지를 지나기 전에는 어떤 경로로도 파일 선택기가 열리지 않는다.
 *   2. "확인하고 계속"을 눌러야 열리고, 그 뒤 업로드는 정상 동작한다.
 *   3. "그만두기"를 누르면 아무것도 전송되지 않는다.
 *   4. Gemini를 쓸 수 없을 때의 오류 안내는 그대로다.
 */
import { beforeEach, describe, expect, test, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DocPhotoCheck } from "./DocPhotoCheck";
import { api } from "../api";

/** 파일 선택기가 실제로 열렸는지를 본다 — input.click()이 불렸는가로 판정한다. */
function watchFilePicker() {
  const clicks: HTMLInputElement[] = [];
  const spy = vi
    .spyOn(HTMLInputElement.prototype, "click")
    .mockImplementation(function (this: HTMLInputElement) {
      clicks.push(this);
    });
  return { clicks, spy };
}

function renderIt() {
  const onChecklist = vi.fn();
  render(<DocPhotoCheck incidentId={1} docStdId={2} onChecklist={onChecklist} />);
  return { onChecklist };
}

const openButton = () => screen.getByRole("button", { name: "서류 사진으로 확인하기" });

beforeEach(() => {
  sessionStorage.clear();
  vi.restoreAllMocks();
  // 데스크톱으로 둔다 — 카메라가 있는 기기면 선택 모달이 한 겹 더 끼어든다.
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: false, media: query, onchange: null,
    addListener: () => {}, removeListener: () => {},
    addEventListener: () => {}, removeEventListener: () => {},
    dispatchEvent: () => false,
  }));
  Object.defineProperty(navigator, "maxTouchPoints", { value: 0, configurable: true });
});

describe("외부 AI 전송 고지", () => {
  test("고지를 지나기 전에는 파일 선택기가 열리지 않는다", async () => {
    const { clicks } = watchFilePicker();
    const verify = vi.spyOn(api, "verifyDocumentPhoto");
    renderIt();

    await userEvent.click(openButton());

    expect(clicks).toHaveLength(0);
    expect(verify).not.toHaveBeenCalled();
    expect(screen.getByText("AI 서류 확인 안내")).toBeTruthy();
  });

  test("고지문이 외부 전송 사실과 남는 기록을 함께 말한다", async () => {
    renderIt();
    await userEvent.click(openButton());

    const notice = screen.getByText("AI 서류 확인 안내").closest(".modal-card")!;
    const text = notice.textContent ?? "";

    // 외부로 간다는 사실을 흐리지 않는다.
    expect(text).toContain("Google Gemini API");
    expect(text).toContain("전송");
    // 저장하지 않는 것과 보내지 않는 것을 뒤섞지 않는다.
    expect(text).toContain("저장하지 않습니다");
    // 실제로 남는 것(상태 + 개수 요약)도 말한다.
    expect(text).toContain("개수 요약");
    // 검증되지 않은 표현을 쓰지 않는다.
    expect(text).not.toContain("완전히 익명");
    expect(text).not.toContain("전송하지 않");
  });

  test("확인하고 계속을 눌러야 파일 선택기가 열린다", async () => {
    const { clicks } = watchFilePicker();
    renderIt();

    await userEvent.click(openButton());
    await userEvent.click(screen.getByRole("button", { name: "확인하고 계속" }));

    expect(clicks).toHaveLength(1);
    expect(clicks[0].type).toBe("file");
  });

  test("그만두기를 누르면 아무것도 전송되지 않는다", async () => {
    const { clicks } = watchFilePicker();
    const verify = vi.spyOn(api, "verifyDocumentPhoto");
    renderIt();

    await userEvent.click(openButton());
    await userEvent.click(screen.getByRole("button", { name: "그만두기" }));

    expect(clicks).toHaveLength(0);
    expect(verify).not.toHaveBeenCalled();
    expect(screen.queryByText("AI 서류 확인 안내")).toBeNull();
  });

  test("한 번 확인하면 같은 세션에서는 다시 묻지 않는다", async () => {
    const { clicks } = watchFilePicker();
    renderIt();

    await userEvent.click(openButton());
    await userEvent.click(screen.getByRole("button", { name: "확인하고 계속" }));
    expect(clicks).toHaveLength(1);

    // 두 번째부터는 고지 없이 바로 선택기로 간다.
    await userEvent.click(openButton());
    expect(screen.queryByText("AI 서류 확인 안내")).toBeNull();
    expect(clicks).toHaveLength(2);
  });

  test("카메라로 찍는 길도 고지를 먼저 지난다", async () => {
    // 손가락으로 만지는 기기: 찍기/고르기 선택 모달이 끼어드는 경로다.
    Object.defineProperty(navigator, "maxTouchPoints", { value: 5, configurable: true });
    const { clicks } = watchFilePicker();
    renderIt();

    await userEvent.click(openButton());
    // 고지가 먼저다 — 선택 모달이 아니다.
    expect(screen.getByText("AI 서류 확인 안내")).toBeTruthy();
    expect(screen.queryByText("사진 찍기")).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "확인하고 계속" }));
    expect(clicks).toHaveLength(0); // 아직 안 열렸다 — 찍기/고르기를 고를 차례다.

    await userEvent.click(screen.getByText("사진 찍기"));
    expect(clicks).toHaveLength(1);
    expect(clicks[0].getAttribute("capture")).toBe("environment");
  });
});

describe("고지를 지난 뒤의 동작", () => {
  test("확인 후 업로드가 정상 동작한다", async () => {
    watchFilePicker();
    const verify = vi.spyOn(api, "verifyDocumentPhoto").mockResolvedValue({
      required_doc_std_id: 2, doc_name: "진료비 영수증", readable: true,
      detected_doc_type: "영수증", language: "영어",
      translation: "치료비 120달러를 결제한 영수증이에요.",
      message: "약관이 요구하는 내용이 모두 확인됐어요.", applied_status: "보유",
      grounded: [], practical: [], checklist: { items: [] } as never,
    } as never);
    const { onChecklist } = renderIt();

    await userEvent.click(openButton());
    await userEvent.click(screen.getByRole("button", { name: "확인하고 계속" }));

    const input = document.querySelector<HTMLInputElement>('input[type=file]:not([capture])')!;
    await userEvent.upload(input, new File(["x"], "receipt.jpg", { type: "image/jpeg" }));

    await waitFor(() => expect(verify).toHaveBeenCalledTimes(1));
    expect(onChecklist).toHaveBeenCalled();
    await screen.findByText("치료비 120달러를 결제한 영수증이에요.");
    // 결과 화면도 외부에서 읽었다는 사실을 말한다.
    expect(screen.getByText(/Google Gemini API가 읽어서 만든/)).toBeTruthy();
  });

  test("Gemini를 쓸 수 없으면 기존 오류 안내가 그대로 뜬다", async () => {
    watchFilePicker();
    vi.spyOn(api, "verifyDocumentPhoto").mockRejectedValue(
      new Error("지금은 사진 확인을 쓸 수 없어요. 서류 상태를 직접 골라주세요.")
    );
    renderIt();

    await userEvent.click(openButton());
    await userEvent.click(screen.getByRole("button", { name: "확인하고 계속" }));

    const input = document.querySelector<HTMLInputElement>('input[type=file]:not([capture])')!;
    await userEvent.upload(input, new File(["x"], "receipt.jpg", { type: "image/jpeg" }));

    // 모달 제목("사진 확인")과 본문이 둘 다 걸리므로 본문만 짚는다.
    await waitFor(() => {
      const message = document.querySelector(".doc-verify__message");
      expect(message?.textContent).toMatch(/확인하지 못했어요|쓸 수 없어요/);
    });
  });
});

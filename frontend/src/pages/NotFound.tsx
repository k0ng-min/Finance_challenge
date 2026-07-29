import { useNavigate } from "react-router-dom";
import { TopBar } from "../components/TopBar";
import { ErrorState } from "../components/ErrorState";

export function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="page">
      <TopBar title="페이지를 찾을 수 없어요" />
      <ErrorState
        code="404"
        title="이 페이지는 없어요"
        message="주소가 바뀌었거나 존재하지 않는 화면이에요. 홈으로 돌아가 다시 시작해주세요."
        actionLabel="홈으로 가기"
        onAction={() => navigate("/")}
      />
    </div>
  );
}

import { FormEvent, useState } from "react";

interface AuthGateProps {
  loading: boolean;
  error: string;
  onLogin: (username: string, password: string) => Promise<void>;
}

export function AuthGate({ loading, error, onLogin }: AuthGateProps) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await onLogin(username, password);
  };

  return (
    <div className="auth-shell">
      <div className="auth-panel">
        <p className="eyebrow">로그인</p>
        <h1>사내 이미지 탐색 도구</h1>
        <p className="muted">
          서버에 저장된 PNG, JPG/JPEG, BMP, GIF, TIFF, WEBP 등 이미지 파일을 폴더 트리, 썸네일, 메타데이터, 검색 조건으로 안전하게 탐색합니다.
        </p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            사용자명
            <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
          </label>
          <label>
            비밀번호
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>
          {error ? <div className="error-box">{error}</div> : null}
          <button type="submit" disabled={loading}>
            {loading ? "로그인 중" : "로그인"}
          </button>
        </form>
      </div>
    </div>
  );
}

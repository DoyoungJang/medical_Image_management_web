import { FormEvent, useState } from "react";

interface AuthGateProps {
  loading: boolean;
  error: string;
  onLogin: (username: string, password: string) => Promise<void>;
  onRegister: (username: string, password: string, signupCode: string) => Promise<void>;
}

export function AuthGate({ loading, error, onLogin, onRegister }: AuthGateProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [signupCode, setSignupCode] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (mode === "register") {
      await onRegister(username, password, signupCode);
      return;
    }
    await onLogin(username, password);
  };

  return (
    <div className="auth-shell">
      <div className="auth-panel">
        <p className="eyebrow">계정</p>
        <h1>의료 이미지 탐색 도구</h1>
        <p className="muted">
          서버에 저장된 이미지 파일을 폴더 트리, 썸네일, 메타데이터 검색 조건으로 안전하게 탐색합니다.
        </p>
        <div className="view-tabs auth-tabs" role="tablist" aria-label="인증 방식">
          <button
            type="button"
            className={mode === "login" ? "active" : "secondary"}
            onClick={() => {
              setMode("login");
              setUsername("admin");
            }}
          >
            로그인
          </button>
          <button
            type="button"
            className={mode === "register" ? "active" : "secondary"}
            onClick={() => {
              setMode("register");
              setUsername("");
            }}
          >
            회원가입
          </button>
        </div>
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
              autoComplete={mode === "register" ? "new-password" : "current-password"}
            />
          </label>
          {mode === "register" ? (
            <label>
              가입 코드
              <input
                value={signupCode}
                onChange={(event) => setSignupCode(event.target.value)}
                autoComplete="one-time-code"
              />
            </label>
          ) : null}
          {error ? <div className="error-box">{error}</div> : null}
          <button type="submit" disabled={loading}>
            {loading ? "처리 중" : mode === "register" ? "가입하기" : "로그인"}
          </button>
        </form>
      </div>
    </div>
  );
}

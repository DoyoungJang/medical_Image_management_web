export const STATUS_LABELS: Record<string, string> = {
  ok: "정상",
  corrupted: "손상됨",
  unreadable: "읽기 불가",
  unsupported: "지원 안 함",
  missing: "누락됨",
};

export const SORT_LABELS: Record<string, string> = {
  filename: "파일명",
  path: "경로",
  file_size: "파일 크기",
  modified_time: "수정 시각",
  width: "너비",
  height: "높이",
};

const SERVER_MESSAGE_LABELS: Record<string, string> = {
  "Admin privileges required.": "관리자 계정만 실행할 수 있습니다.",
  "Authentication is disabled.": "현재 서버에서 인증이 비활성화되어 있습니다.",
  "Authentication required.": "로그인이 필요합니다.",
  "AUTH_PASSWORD or AUTH_PASSWORD_HASH is not configured.": "서버 인증 비밀번호가 설정되지 않았습니다.",
  "AUTH_PASSWORD_HASH is not configured.": "서버 인증 비밀번호 해시가 설정되지 않았습니다.",
  "Current password is incorrect.": "현재 비밀번호가 올바르지 않습니다.",
  "Image file is unavailable.": "이미지 파일을 사용할 수 없습니다.",
  "Image not found.": "이미지를 찾을 수 없습니다.",
  "Invalid credentials.": "사용자명 또는 비밀번호가 올바르지 않습니다.",
  "Invalid password hash configuration.": "서버 인증 비밀번호 해시 설정이 올바르지 않습니다.",
  "Invalid username or password.": "사용자명 또는 비밀번호가 올바르지 않습니다.",
  "Login is required.": "로그인이 필요합니다.",
  "Password hash is invalid.": "서버 인증 비밀번호 해시가 올바르지 않습니다.",
  "Signup code is incorrect.": "가입 코드가 올바르지 않습니다.",
  "Signup code is not configured.": "가입 코드가 아직 설정되지 않았습니다. 관리자에게 문의하세요.",
  "Settings database is unavailable.": "설정 데이터베이스를 사용할 수 없습니다.",
  "This username is reserved.": "이 사용자명은 사용할 수 없습니다.",
  "Thumbnail could not be generated for this PNG file.": "이 이미지 파일의 썸네일을 생성할 수 없습니다.",
  "User account was not found.": "사용자 계정을 찾을 수 없습니다.",
  "User database is unavailable.": "사용자 데이터베이스를 사용할 수 없습니다.",
  "Username is required.": "사용자명을 입력하세요.",
  "Username already exists.": "이미 사용 중인 사용자명입니다.",
  "A scan is already running or was triggered too recently.": "이미 스캔 중이거나 너무 빠르게 재요청했습니다.",
};

const FIELD_LABELS: Record<string, string> = {
  current_password: "현재 비밀번호",
  new_password: "새 비밀번호",
  password: "비밀번호",
  signup_code: "가입 코드",
  username: "사용자명",
};

export function statusLabel(status: string | null | undefined): string {
  if (!status) {
    return "-";
  }
  return STATUS_LABELS[status] ?? status;
}

export function booleanLabel(value: boolean | null | undefined): string {
  if (value === true) {
    return "예";
  }
  if (value === false) {
    return "아니요";
  }
  return "-";
}

export function translateServerMessage(message: unknown): string {
  if (typeof message === "string") {
    return SERVER_MESSAGE_LABELS[message] ?? message;
  }

  if (Array.isArray(message)) {
    const validationMessages = message.map(validationErrorLabel).filter(Boolean);
    if (validationMessages.length) {
      return validationMessages.join(" ");
    }
  }

  if (message && typeof message === "object") {
    const record = message as Record<string, unknown>;
    if (typeof record.msg === "string") {
      return validationErrorLabel(record) || record.msg;
    }
    if (typeof record.detail === "string") {
      return translateServerMessage(record.detail);
    }
  }

  return "요청을 처리하지 못했습니다.";
}

function validationErrorLabel(error: unknown): string {
  if (!error || typeof error !== "object") {
    return "";
  }

  const record = error as Record<string, unknown>;
  const field = validationFieldLabel(record.loc);
  const type = typeof record.type === "string" ? record.type : "";
  const msg = typeof record.msg === "string" ? record.msg : "";

  if (type.includes("missing")) {
    return `${field}을(를) 입력하세요.`;
  }
  if (type.includes("string_too_short")) {
    return `${field}이(가) 너무 짧습니다.`;
  }
  if (type.includes("string_too_long")) {
    return `${field}이(가) 너무 깁니다.`;
  }
  if (type.includes("string_pattern_mismatch")) {
    return `${field} 형식이 올바르지 않습니다.`;
  }

  return msg ? `${field}: ${msg}` : "";
}

function validationFieldLabel(loc: unknown): string {
  if (!Array.isArray(loc) || !loc.length) {
    return "입력값";
  }

  const fieldName = String(loc[loc.length - 1]);
  return FIELD_LABELS[fieldName] ?? fieldName;
}

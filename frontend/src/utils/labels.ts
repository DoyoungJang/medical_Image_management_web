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
  "Invalid credentials.": "사용자명 또는 비밀번호가 올바르지 않습니다.",
  "Authentication required.": "로그인이 필요합니다.",
  "AUTH_PASSWORD_HASH is not configured.": "서버 인증 비밀번호 해시가 설정되지 않았습니다.",
  "Invalid password hash configuration.": "서버 인증 비밀번호 해시 설정이 올바르지 않습니다.",
  "Image not found.": "이미지를 찾을 수 없습니다.",
  "Image file is unavailable.": "이미지 파일을 사용할 수 없습니다.",
  "A scan is already running or was triggered too recently.": "이미 스캔 중이거나 너무 빠르게 재요청했습니다.",
  "Thumbnail could not be generated for this PNG file.": "이 이미지 파일의 썸네일을 생성할 수 없습니다.",
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
    return "아니오";
  }
  return "-";
}

export function translateServerMessage(message: string): string {
  return SERVER_MESSAGE_LABELS[message] ?? message;
}

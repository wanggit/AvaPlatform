from __future__ import annotations

"""生成、校验和撤销数字员工访问平台网关的服务令牌。"""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass


class TokenError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


@dataclass(frozen=True)
class EmployeeServiceClaims:
    employee_id: str
    profile_id: str
    issued_at: int
    expires_at: int
    token_id: str


class EmployeeServiceTokenManager:
    def __init__(self, secret: str) -> None:
        self.secret = secret.encode("utf-8")
        self._revoked_token_ids: set[str] = set()

    def issue(self, employee_id: str, profile_id: str, *, ttl_seconds: int = 86_400) -> str:
        now = int(time.time())
        claims = {
            "employee_id": employee_id,
            "profile_id": profile_id,
            "iat": now,
            "exp": now + ttl_seconds,
            "jti": hashlib.sha256(f"{employee_id}:{profile_id}:{now}".encode("utf-8")).hexdigest()[:24],
        }
        payload = _b64(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
        signature = _b64(hmac.new(self.secret, payload.encode("ascii"), hashlib.sha256).digest())
        return f"{payload}.{signature}"

    def verify(self, token: str) -> EmployeeServiceClaims:
        try:
            payload, signature = token.split(".", 1)
        except ValueError as exc:
            raise TokenError("令牌格式无效") from exc

        expected = _b64(hmac.new(self.secret, payload.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature):
            raise TokenError("令牌签名无效")

        claims = json.loads(_unb64(payload))
        if claims["jti"] in self._revoked_token_ids:
            raise TokenError("令牌已吊销")
        if int(claims["exp"]) < int(time.time()):
            raise TokenError("令牌已过期")
        return EmployeeServiceClaims(
            employee_id=claims["employee_id"],
            profile_id=claims["profile_id"],
            issued_at=int(claims["iat"]),
            expires_at=int(claims["exp"]),
            token_id=claims["jti"],
        )

    def revoke(self, token: str) -> None:
        claims = self.verify(token)
        self._revoked_token_ids.add(claims.token_id)

"""Principals and tokens — the tenant comes from the token, never a header.

v2.4's service read `X-Tenant` and believed it. That made every isolation test
a test between two values the client chose, and it made the test suite a
worked example of the wrong pattern. §14.5 is explicit: the tenant is derived
from the verified credential, and a header may only *narrow* what the token
already permits.
"""
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    tenant: str
    role: str = "tenant"          # "tenant" | "admin"
    subject: str = ""
    expires_at: float = 0.0       # epoch seconds; 0 means "no expiry" and is a bug
    issued_at: float = 0.0

    @property
    def is_admin(self):
        return self.role == "admin"

    def expired(self, now=None):
        now = time.time() if now is None else now
        return self.expires_at != 0.0 and now >= self.expires_at


class Tokens:
    """A token registry. In production this is a JWKS and a signature check;
    here it is a mapping, because what is being tested is the *rule*, not RSA."""

    def __init__(self, mapping=None, ttl=900, clock=None, store=None):
        self.mapping = dict(mapping or {})
        self.ttl = ttl
        self.clock = clock or time.time
        self.store = store          # when given, revocation is shared and durable
        self.revoked = set()        # fallback for a process with no store

    def issue(self, token, tenant, role="tenant", subject="", ttl=None):
        now = self.clock()
        principal = Principal(
            tenant=tenant, role=role, subject=subject,
            issued_at=now, expires_at=now + (self.ttl if ttl is None else ttl))
        self.mapping[token] = principal
        if self.store is not None:
            self.store.store_token(token, tenant, role, subject,
                                   principal.issued_at, principal.expires_at)
        return token

    def revoke(self, token):
        """Revocation takes effect on the next request, in every process.

        v2.6 kept this set in memory, so a revoked token was rejected by the
        process that revoked it and accepted by every other — a revocation
        list that does not revoke.
        """
        self.revoked.add(token)
        principal = self.mapping.pop(token, None)
        if self.store is not None:
            self.store.revoke_token(token, principal.tenant if principal else "unknown")

    def rotate(self, token, **kwargs):
        """Issue a replacement and revoke the old one in the same step."""
        old = self.mapping.get(token)
        if old is None:
            return None
        self.revoke(token)
        return self.issue(token + "_r", old.tenant, old.role, old.subject, **kwargs)

    def principal(self, headers):
        """None when the credential is absent, unknown, revoked or expired."""
        raw = headers.get("Authorization") or headers.get("authorization") or ""
        if not raw.lower().startswith("bearer "):
            return None
        token = raw[7:].strip()
        if token in self.revoked:
            return None
        if self.store is not None and self.store.is_revoked(token):
            return None
        principal = self.mapping.get(token)
        if principal is None and self.store is not None:
            record = self.store.token_record(token)
            if record is not None:
                principal = Principal(
                    tenant=record["tenant_id"], role=record["role"],
                    subject=record["subject"], issued_at=record["issued_at"],
                    expires_at=record["expires_at"])
        if principal is None or principal.expired(self.clock()):
            return None
        return principal


class AuthError(Exception):
    def __init__(self, code, status):
        super().__init__(code)
        self.code = code
        self.status = status


def resolve(headers, tokens, requested_tenant=None):
    """The tenant a request acts on, or an AuthError.

    A header naming another tenant is an override, and only an admin may make
    one. Anything else is a 403 — the request is authenticated and forbidden,
    which is a different thing from the 404 a cross-tenant *read* returns so
    that it does not disclose existence.
    """
    principal = tokens.principal(headers)
    if principal is None:
        raise AuthError("UNAUTHENTICATED", 401)
    if requested_tenant and requested_tenant != principal.tenant:
        if not principal.is_admin:
            raise AuthError("TENANT_OVERRIDE_FORBIDDEN", 403)
        return requested_tenant
    return principal.tenant

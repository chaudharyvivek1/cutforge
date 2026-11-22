"""Principals and tokens — the tenant comes from the token, never a header.

v2.4's service read `X-Tenant` and believed it. That made every isolation test
a test between two values the client chose, and it made the test suite a
worked example of the wrong pattern. §14.5 is explicit: the tenant is derived
from the verified credential, and a header may only *narrow* what the token
already permits.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    tenant: str
    role: str = "tenant"          # "tenant" | "admin"
    subject: str = ""

    @property
    def is_admin(self):
        return self.role == "admin"


class Tokens:
    """A token registry. In production this is a JWKS and a signature check;
    here it is a mapping, because what is being tested is the *rule*, not RSA."""

    def __init__(self, mapping=None):
        self.mapping = dict(mapping or {})

    def issue(self, token, tenant, role="tenant", subject=""):
        self.mapping[token] = Principal(tenant=tenant, role=role, subject=subject)
        return token

    def principal(self, headers):
        """None when the credential is absent or unknown — never a default tenant."""
        raw = headers.get("Authorization") or headers.get("authorization") or ""
        if not raw.lower().startswith("bearer "):
            return None
        return self.mapping.get(raw[7:].strip())


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

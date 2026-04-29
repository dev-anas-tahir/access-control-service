from dataclasses import dataclass


@dataclass(frozen=True)
class ScopeKey:
    """Resource:action permission identifier (e.g. "users:read")."""

    resource: str
    action: str

    def __post_init__(self) -> None:
        if not self.resource or not self.action:
            raise ValueError("resource and action must be non-empty")
        if ":" in self.resource or ":" in self.action:
            raise ValueError("resource and action must not contain ':'")

    @property
    def key(self) -> str:
        return f"{self.resource}:{self.action}"

    @classmethod
    def parse(cls, scope: str) -> "ScopeKey":
        if scope.count(":") != 1:
            raise ValueError(f"Invalid scope key: {scope!r}")
        resource, action = scope.split(":")
        return cls(resource=resource, action=action)

    def __str__(self) -> str:
        return self.key

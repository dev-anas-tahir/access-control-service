from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        if "@" not in self.value:
            raise ValueError(f"Invalid email: {self.value!r}")
        local, _, domain = self.value.partition("@")
        if not local or not domain or "." not in domain:
            raise ValueError(f"Invalid email: {self.value!r}")

    def __str__(self) -> str:
        return self.value

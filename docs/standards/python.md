# Python Standards

Applies to all Python services in the monorepo.

## Version & Tooling

- Python **3.13** (enforced in `pyproject.toml` — `>=3.13,<3.14`)
- Package management: **uv** workspaces (`uv sync` at repo root)
- Linter/formatter: **Ruff** (`line-length = 88`, rules `E, F, I`, target `py313`)
- Tests: **pytest** with `asyncio_mode = "auto"`

## Type Hints

Use modern syntax throughout — no legacy imports:

```python
# correct
def foo(items: list[str], value: int | None) -> dict[str, int]: ...

# wrong
from typing import List, Optional, Dict
def foo(items: List[str], value: Optional[int]) -> Dict[str, int]: ...
```

All functions and methods must have return type annotations.

## Async

All route handlers, use cases, and repository methods are `async def`. Do not mix sync and async DB calls.

```python
# correct
async def find_by_username(self, username: str) -> User | None:
    result = await self._session.execute(select(UserORM).where(...))
    ...

# wrong — blocks the event loop
def find_by_username(self, username: str) -> User | None:
    ...
```

## Domain Layer Rule

The `domain/` layer of any bounded context must have **zero** imports from:
- `fastapi`
- `sqlalchemy`
- `redis`
- `pyjwt` / `cryptography`

Use `typing.Protocol` for ports. Depend on abstractions, not implementations.

## Docstrings

Google style. One-line summary only for simple methods. Omit if the function name and signature are self-explanatory.

```python
def hash(self, plain: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
```

## Comments

Write comments only for non-obvious WHY, not WHAT. A comment that re-states the code is noise.

## Pydantic Models

- Request schemas: `BaseModel`
- Response schemas from ORM objects: inherit `OrmSchema` (`model_config = ConfigDict(from_attributes=True)`)
- Use `Field(min_length=..., max_length=...)` for string constraints — not custom validators unless logic is needed

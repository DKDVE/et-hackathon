"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.engine import get_db

DbDep = Annotated[Session, Depends(get_db)]

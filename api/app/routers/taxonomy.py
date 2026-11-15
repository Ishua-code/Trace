"""GET /api/taxonomy: read-only canonical lists for dropdowns (single source: engine/taxonomy.py)."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.engine import taxonomy as t

router = APIRouter(prefix="/api", tags=["taxonomy"])


class Option(BaseModel):
    code: str
    label: str


class ProcessOption(BaseModel):
    name: str
    department_id: int


class DepartmentOption(BaseModel):
    id: int
    name: str


class TaxonomyOut(BaseModel):
    products: list[str]
    lines: list[str]
    departments: list[DepartmentOption]
    processes: list[ProcessOption]
    root_causes: list[Option]
    defect_codes: list[Option]


@router.get("/taxonomy", response_model=TaxonomyOut)
def get_taxonomy() -> TaxonomyOut:
    return TaxonomyOut(
        products=list(t.PRODUCTS),
        lines=list(t.LINES),
        departments=[DepartmentOption(id=i, name=n) for i, n in t.DEPARTMENTS.items()],
        processes=[ProcessOption(name=p, department_id=d) for p, d in t.PROCESS_DEPARTMENT.items()],
        root_causes=[Option(code=c, label=l) for c, l in t.ROOT_CAUSE_CATEGORIES.items()],
        defect_codes=[Option(code=c, label=l) for c, l in t.DEFECT_CODES.items()],
    )

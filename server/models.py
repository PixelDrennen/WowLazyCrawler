from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    region: Literal['us', 'eu', 'kr', 'tw'] = 'us'
    realms: list[str] = Field(default_factory=list, max_length=2000)
    selling_realms: list[str] = Field(default_factory=list, max_length=2000)
    demo_mode: bool = False
    @field_validator("demo_mode", mode="before")
    @classmethod
    def live_only(cls, value):
        return False  # Retain compatibility with older configs without displaying simulated observations.

    coverage_mode: Literal['all_clusters'] = 'all_clusters'
    wow_path: str = Field(default='', max_length=1000)
    companion_enabled: bool = True
    theme: Literal['grove','spectral','ember'] = 'grove'
    scan_concurrency: int = Field(default=3, ge=1, le=6)
    budget_gold: float = Field(default=50000, ge=0, le=1e9)
    max_item_gold: float = Field(default=5000, ge=0, le=1e9)
    min_profit_gold: float = Field(default=500, ge=0, le=1e9)
    min_roi: float = Field(default=20, ge=0, le=100000)
    fee_percent: float = Field(default=5, ge=0, le=100)
    deposit_gold: float = Field(default=1, ge=0, le=1e6)
    max_age_hours: int = Field(default=12, ge=1, le=168)
    max_context_age_hours: int = Field(default=72, ge=24, le=168)
    min_sold_day: float = Field(default=0.01, ge=0, le=1e9)
    max_sale_days: int = Field(default=90, ge=1, le=3650)
    interval_minutes: int = Field(default=180, ge=60, le=1440)
    retention_days: int = Field(default=30, ge=1, le=365)
    scheduled: bool = False
    tsm_enabled: bool = True
    blizzard_enabled: bool = False
    help_enabled: bool = True

    @field_validator('realms', 'selling_realms')
    @classmethod
    def slugs(cls, values):
        import re
        for value in values:
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', value):
                raise ValueError('Use realm URL slugs, for example area-52 or stormrage')
        return list(dict.fromkeys(values))


class Credentials(BaseModel):
    client_id: str = Field(max_length=200)
    client_secret: str = Field(max_length=300)


class Login(BaseModel):
    token: str = Field(min_length=1, max_length=500)


class Material(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    item_id: int = Field(gt=0)
    quantity: float = Field(gt=0, le=1e6)
    owned: float = Field(default=0, ge=0, le=1e9)
    unit_cost_gold: float | None = Field(default=None, ge=0, le=1e9)


class Recipe(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    name: str = Field(min_length=1, max_length=120)
    character: str = Field(default='', max_length=80)
    profession: str = Field(default='', max_length=80)
    output_item_id: int = Field(gt=0)
    crafts: int = Field(default=1, ge=1, le=10000)
    expected_yield: float = Field(default=1, gt=0, le=1000)
    sale_price_gold: float = Field(ge=0, le=1e9)
    concentration: float = Field(default=0, ge=0, le=10000)
    baseline_profit_gold: float | None = Field(default=None, ge=-1e9, le=1e9)
    materials: list[Material] = Field(min_length=1, max_length=100)
    assumptions: str = Field(default='Manual estimate; validate quality and yield in CraftSim.', max_length=1000)

    @field_validator('materials')
    @classmethod
    def unique(cls, materials):
        if len({m.item_id for m in materials}) != len(materials):
            raise ValueError('Consolidate duplicate item IDs before importing')
        return materials

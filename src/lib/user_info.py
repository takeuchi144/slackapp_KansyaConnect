from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class UserInfo(BaseModel):
    user_id: str
    team_id: str = ''
    user_name: str = ''
    real_name: str = ''
    display_name: str = ''
    email: str = ''
    total_points: int = 0
    daily_points_given: int = 0
    last_reset_date: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserInfo':
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return self.dict()

    @property
    def has_empty_fields(self) -> bool:
        """空白の要素があるかどうかを判定"""
        return any(
            not getattr(self, field)
            for field in ['team_id', 'user_name', 'real_name', 'display_name', 'email']
        )

    def get(self, key: str, default: Any = None) -> Any:
        """指定されたキーの値を取得"""
        return getattr(self, key, default)
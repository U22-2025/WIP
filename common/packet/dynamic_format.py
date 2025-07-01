from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class FieldDef:
    name: str
    length: int
    meta: Dict[str, Any] | None = None

class DynamicFormat:
    """動的にフィールド定義を読み込むフォーマットクラス"""
    def __init__(self, fields: List[FieldDef]):
        self.fields = fields

    @classmethod
    def load(cls, fields: List[Dict[str, Any]]) -> 'DynamicFormat':
        """フィールド定義からDynamicFormatを生成する"""
        names = [f.get('name') for f in fields]
        if len(names) != len(set(names)):
            raise ValueError('fields の name が重複しています')
        field_defs: List[FieldDef] = []
        for f in fields:
            name = f.get('name')
            length = f.get('length')
            if length is None or length < 1:
                raise ValueError('length は 1 以上でなければなりません')
            meta = {k: v for k, v in f.items() if k not in {'name', 'length'}}
            field_defs.append(FieldDef(name=name, length=length, meta=meta or None))
        return cls(field_defs)

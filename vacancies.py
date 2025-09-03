from dataclasses import dataclass, field
from typing import List, Dict
import json, os

@dataclass
class Vacancy:
    key: str
    title: str
    description: str
    requirements: List[str]
    nice_to_have: List[str] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=dict)

def load_vacancies(path: str = "vacancies.json") -> Dict[str, Vacancy]:
    data = json.load(open(path, "r", encoding="utf-8"))
    res: Dict[str, Vacancy] = {}
    for v in data:
        obj = Vacancy(**v)
        res[obj.key] = obj
    return res

VACANCIES: Dict[str, Vacancy] = load_vacancies()
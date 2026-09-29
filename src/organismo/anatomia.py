from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List


class EstadoBiologico(str, Enum):
    REPOSO = "reposo"          # ⚫ Negro (Basal / Inactivo)
    ACTIVIDAD = "actividad"    # 🟢 Verde (Trabajando)
    APRENDIENDO = "aprendiendo"# 🟡 Amarillo (Morfogénesis / Tests)
    FALLO = "fallo"            # 🔴 Rojo (Error)


@dataclass
class Celula:
    id: str
    nombre: str
    especialidad: str
    estado: EstadoBiologico = EstadoBiologico.REPOSO
    herramientas: List[str] = field(default_factory=list)
    descripcion: str = ""
    ruta_dir: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["estado"] = self.estado.value
        return d


@dataclass
class Tejido:
    id: str
    nombre: str
    funcion: str
    estado: EstadoBiologico = EstadoBiologico.REPOSO
    celulas: Dict[str, Celula] = field(default_factory=dict)

    def agregar_celula(self, celula: Celula) -> None:
        self.celulas[celula.id] = celula

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "funcion": self.funcion,
            "estado": self.estado.value,
            "celulas": [c.to_dict() for c in self.celulas.values()],
        }


@dataclass
class Organo:
    id: str
    nombre: str
    sistema: str
    estado: EstadoBiologico = EstadoBiologico.REPOSO
    tejidos: Dict[str, Tejido] = field(default_factory=dict)

    def agregar_tejido(self, tejido: Tejido) -> None:
        self.tejidos[tejido.id] = tejido

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "sistema": self.sistema,
            "estado": self.estado.value,
            "tejidos": [t.to_dict() for t in self.tejidos.values()],
        }

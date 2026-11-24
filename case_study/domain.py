"""Domain enumerations of the case study.

Java: TCity, TColor, TMotor, TPanorama, TSpeed, TType_Danger, TType_Quality_Desire, TColor_Route,
TMy_Collections.

Enum members keep the Java names; ``ordinal`` is the Java ``ordinal()`` (city numbers stored in the
beliefs are city ordinals) and ``values()`` the Java ``values()``.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List


class _JavaEnum(Enum):
    """Base of the domain enums: adds the Java-style ``ordinal`` (declaration order), ``values()``,
    ``value_of(name)`` and ``str()`` = name."""

    @property
    def ordinal(self) -> int:
        cache = type(self).__dict__.get("_ordinals")
        if cache is None:
            cache = {m: i for i, m in enumerate(type(self))}
            setattr(type(self), "_ordinals", cache)
        return cache[self]

    @classmethod
    def values(cls) -> List["_JavaEnum"]:
        return list(cls)

    @classmethod
    def value_of(cls, name: str) -> "_JavaEnum":
        try:
            return cls[name]
        except KeyError:
            raise ValueError(f"No enum constant {cls.__name__}.{name}") from None

    def __str__(self) -> str:       # Java toString()
        return self.name


class TCity(_JavaEnum):
    """The 47 cities of the map. The declaration order is the Java ordinal: beliefs such as
    ``BL_Position_City`` store the ordinal.
    """
    Lisboa = 0
    Madrid = 1
    Cadiz = 2
    Barcelona = 3
    Pamplona = 4
    Brest = 5
    Paris = 6
    Dieppe = 7
    Marseille = 8
    Zurich = 9
    Rome = 10
    Venice = 11
    Palermo = 12
    Brindisi = 13
    Frankfurt = 14
    Munchen = 15
    Wien = 16
    Budapest = 17
    Zacrab = 18
    Sarajevo = 19
    Bucaresti = 20
    Sofia = 21
    Athina = 22
    Smyrna = 23
    Ancora = 24
    Costantinople = 25
    Savastopol = 26
    Sochi = 27
    Rostow = 28
    Bruxelles = 29
    London = 30
    Edinburgh = 31
    Amsterdam = 32
    Essen = 33
    Berlin = 34
    Kodenilavn = 35
    Danzic = 36
    Stockholm = 37
    Warszawa = 38
    Rica = 39
    Wilno = 40
    Smolensk = 41
    Moskva = 42
    Petrocrad = 43
    Kyiv = 44
    Kharkov = 45
    Erzurum = 46


class TColor(_JavaEnum):
    """Colours of the routes; each colour fixes panorama, speed and allowed motors (see ``MyCollections``).
    """
    Red = 0
    Green = 1
    Yellow = 2
    Orange = 3
    Black = 4
    Blue = 5
    Violet = 6
    White = 7


class TMotor(_JavaEnum):
    """Motor types; ``get_value()`` is the pollution value used by the quality filter (12.5 / 75 / 125)."""
    Electric = 0
    Hybrid = 1
    Diesel = 2

    def get_value(self) -> float:
        return {TMotor.Electric: 12.5, TMotor.Hybrid: 75.0, TMotor.Diesel: 125.0}[self]


class TPanorama(_JavaEnum):
    """Panorama quality of a route; ``get_value()`` = 0.3 / 0.6 / 0.9."""
    Limited = 0
    Fair = 1
    Spectacular = 2

    def get_value(self) -> float:
        return {TPanorama.Limited: 0.3, TPanorama.Fair: 0.6, TPanorama.Spectacular: 0.9}[self]


class TSpeed(_JavaEnum):
    """Speed class of a route; ``get_value()`` = 1 / 2 / 3 steps per move."""
    Small = 0
    Medium = 1
    High = 2

    def get_value(self) -> int:
        return {TSpeed.Small: 1, TSpeed.Medium: 2, TSpeed.High: 3}[self]


class TTypeDanger(_JavaEnum):
    """Kinds of danger the traffic control can report; the index is the number typed as first answer."""
    Unknown = 0
    Roks_on_the_Road = 1
    Car_Accident_on_the_Road = 2


class TTypeQualityDesire(_JavaEnum):
    """Quality criteria of the case study (motor, panorama, speed)."""
    Motor = 0
    Panorama = 1
    Speed = 2


class TColorRoute:
    """Java: TColor_Route."""

    def __init__(self, color: TColor, panorama: TPanorama, speed: TSpeed):
        self.color = color
        self.speed = speed
        self.motors: List[TMotor] = []
        self.panorama = panorama


class MyCollections:
    """Java: TMy_Collections (only ``Color_Ruotes`` is used by the environment)."""

    def __init__(self) -> None:
        self.color_ruotes: Dict[TColor, TColorRoute] = {}
        self.locomotive_values = {TMotor.Electric: 0.1, TMotor.Hybrid: 0.5, TMotor.Diesel: 1.0}
        self.panorama_values = {TPanorama.Limited: 0.3, TPanorama.Fair: 0.6, TPanorama.Spectacular: 0.9}
        self.velocity_values = {TSpeed.Small: 0.3, TSpeed.Medium: 0.6, TSpeed.High: 0.9}
        self.station_values = {city: i for i, city in enumerate(TCity)}
        self._initialize_color_ruotes()

    def _initialize_color_ruotes(self) -> None:
        """Fill the colour -> (panorama, speed, motors) table of the route colours."""
        def add(color: TColor, panorama: TPanorama, speed: TSpeed, *motors: TMotor) -> None:
            route = TColorRoute(color, panorama, speed)
            route.motors.extend(motors)
            self.color_ruotes[color] = route

        add(TColor.Red, TPanorama.Limited, TSpeed.High, TMotor.Diesel)
        add(TColor.Green, TPanorama.Fair, TSpeed.Medium, TMotor.Electric, TMotor.Hybrid)
        add(TColor.Yellow, TPanorama.Spectacular, TSpeed.Small, TMotor.Electric, TMotor.Hybrid)
        add(TColor.Orange, TPanorama.Fair, TSpeed.Medium, TMotor.Diesel)
        add(TColor.Black, TPanorama.Limited, TSpeed.Small, TMotor.Diesel)
        add(TColor.Blue, TPanorama.Limited, TSpeed.Medium, TMotor.Electric)
        add(TColor.Violet, TPanorama.Fair, TSpeed.High, TMotor.Hybrid)
        add(TColor.White, TPanorama.Fair, TSpeed.Medium, TMotor.Electric)

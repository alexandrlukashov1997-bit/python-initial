from enum import StrEnum


class BodyType(StrEnum):
    SEDAN = "sedan"
    HATCHBACK = "hatchback"
    WAGON = "wagon"
    SUV = "suv"
    COUPE = "coupe"
    CONVERTIBLE = "convertible"
    PICKUP = "pickup"
    VAN = "van"
    MINIVAN = "minivan"


class EngineType(StrEnum):
    PETROL = "petrol"
    DIESEL = "diesel"
    HYBRID = "hybrid"
    ELECTRIC = "electric"
    LPG = "lpg"


class DriveType(StrEnum):
    FWD = "fwd"
    RWD = "rwd"
    AWD = "awd"


class TransmissionType(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    CVT = "cvt"
    ROBOT = "robot"


class CarStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    SOLD = "sold"
    ARCHIVED = "archived"

from dataclasses import dataclass


def meters_to_degrees(meters: float) -> float:
    # Note: Dirty and unreliable, but should be sufficient for the sake of population generation
    return 0.82/1504 * meters/60


def degrees_to_meters(degrees: float) -> float:
    return degrees * 60 / (0.82/1504)


class Distance:
    meters: float

    def __init__(
            self, *,
            meters: float = 0,
            kilometers: float = 0.,
            centimeters: float = 0.,
            geo_degrees: float = 0.,
            geo_minutes: float = 0.,
    ) -> None:
        self.meters = meters + kilometers * 1000 + centimeters / 100 + degrees_to_meters(geo_minutes + geo_degrees*60)

    @property
    def kilometers(self) -> float:
        return self.meters / 1000

    @property
    def centimeters(self) -> float:
        return self.meters * 100

    @property
    def degrees(self) -> float:
        return meters_to_degrees(self.meters)

    @property
    def minutes(self):
        return self.degrees * 60


class Speed:
    def __init__(self, distance_per_hour: Distance) -> None:
        self.distance_per_hour = distance_per_hour

    @property
    def distance_per_minute(self) -> Distance:
        return Distance(meters=self.distance_per_hour.meters / 60)

    @property
    def distance_per_second(self) -> Distance:
        return Distance(meters=self.distance_per_minute.meters / 60)


@dataclass(frozen=True)
class Coordinates:
    latitude: float
    longitude: float

    @property
    def x(self) -> float:
        return self.longitude

    @property
    def y(self) -> float:
        return self.latitude

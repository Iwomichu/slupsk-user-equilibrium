from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean

import h3

from distance import Coordinates


@dataclass(frozen=True)
class Cluster:
    h3_hex_id: str
    centre: Coordinates
    points: list[Coordinates]

    @staticmethod
    def clusterize_points(points: list[Coordinates], resolution: int) -> list[Cluster]:
        points_by_hex_id = defaultdict(list)
        clusters = []
        for point in points:
            hex_id = h3.geo_to_h3(lat=point.latitude, lng=point.longitude, resolution=resolution)
            points_by_hex_id[hex_id].append(point)

        for hex_id, points in points_by_hex_id.items():
            latitudes = map(lambda point_: point_.latitude, points)
            longitudes = map(lambda point_: point_.longitude, points)
            clusters.append(
                Cluster(
                    h3_hex_id=hex_id,
                    points=points,
                    centre=Coordinates(latitude=mean(latitudes), longitude=mean(longitudes))
                )
            )

        return clusters

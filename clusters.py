from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean
from typing import List, Dict

import h3

from distance import Coordinates
from types import ClusterId, ClusterCentreStrategy


@dataclass(frozen=True)
class Cluster:
    h3_hex_id: ClusterId
    centre: Coordinates
    points: List[Coordinates]

    @staticmethod
    def group_points(points: List[Coordinates], resolution: int) -> Dict[str, List[Coordinates]]:
        points_by_hex_id = defaultdict(list)
        for point in points:
            hex_id = h3.geo_to_h3(lat=point.latitude, lng=point.longitude, resolution=resolution)
            points_by_hex_id[hex_id].append(point)
        return points_by_hex_id

    @staticmethod
    def generate_cluster_centre(
            grouped_points: Dict[str, List[Coordinates]],
            strategy: ClusterCentreStrategy,
    ) -> Dict[str, Coordinates]:
        if strategy in (ClusterCentreStrategy.MEAN,):
            clusters = {}
            for hex_id, points in grouped_points.items():
                latitudes = map(lambda point_: point_.latitude, points)
                longitudes = map(lambda point_: point_.longitude, points)
                clusters[hex_id] = Coordinates(latitude=mean(latitudes), longitude=mean(longitudes))
            return clusters
        elif strategy in (ClusterCentreStrategy.HEXAGON_CENTER,):
            return {hex_id: Coordinates(*h3.h3_to_geo(hex_id)) for hex_id in grouped_points.keys()}

    @staticmethod
    def create_clusters(
            points_by_hex_id: Dict[str, List[Coordinates]],
            centres_by_hex_id: Dict[str, Coordinates],
            strategy: ClusterCentreStrategy,
    ) -> List[Cluster]:
        return [
            Cluster(h3_hex_id=hex_id, centre=centres_by_hex_id[hex_id], points=points_by_hex_id[hex_id])
            for hex_id in points_by_hex_id.keys()
        ]

    @staticmethod
    def clusterize_points(points: List[Coordinates], resolution: int, strategy: ClusterCentreStrategy) -> List[Cluster]:
        points_by_hex_id = Cluster.group_points(points, resolution)
        centres_by_hex_id = Cluster.generate_cluster_centre(points_by_hex_id, strategy)
        return Cluster.create_clusters(points_by_hex_id, centres_by_hex_id, strategy)

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from statistics import mean
from typing import List, Dict

import h3
import networkx
import osmnx.distance

from distance import Coordinates


NodeId = int
ClusterId = str


class ClusterCentreStrategy(str, Enum):
    MEAN = 'MEAN'
    HEXAGON_CENTER = 'HEXAGON_CENTER'


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


class PathAtlas:
    def __init__(self) -> None:
        self.path_from_cluster_id_to_cluster_id: Dict[ClusterId, Dict[ClusterId, List[NodeId]]] = defaultdict(dict)

    def add_path(self, from_cluster: ClusterId, to_cluster: ClusterId, path: List[NodeId]) -> None:
        self.path_from_cluster_id_to_cluster_id[from_cluster][to_cluster] = path
        self.path_from_cluster_id_to_cluster_id[to_cluster][from_cluster] = path

    def path_exists(self, from_cluster: ClusterId, to_cluster: ClusterId) -> bool:
        return to_cluster in self.path_from_cluster_id_to_cluster_id[from_cluster].keys()

    def get_path(self, from_cluster: ClusterId, to_cluster: ClusterId) -> List[NodeId]:
        return self.path_from_cluster_id_to_cluster_id[from_cluster][to_cluster]

    def get_paths(self) -> List[List[NodeId]]:
        return [
            list(path)
            for paths_from_cluster in self.path_from_cluster_id_to_cluster_id.values()
            for path in paths_from_cluster.values()
        ]


def get_paths_between_clusters(
        graph: networkx.MultiDiGraph,
        clusters: List[Cluster],
) -> PathAtlas:
    atlas = PathAtlas()
    clusters_by_hex_id = {cluster.h3_hex_id: cluster for cluster in clusters}
    cluster_centroid_graph_node_ids_by_hex_id = {
        cluster.h3_hex_id: osmnx.distance.nearest_nodes(graph, cluster.centre.longitude, cluster.centre.latitude)
        for cluster in clusters
    }
    for cluster in clusters:
        neighbours: List[Cluster] = [
            clusters_by_hex_id[neighbour_hex_id]
            for neighbour_hex_id in h3.k_ring(cluster.h3_hex_id, k=1)
            if neighbour_hex_id in clusters_by_hex_id.keys()
        ]
        for neighbour in neighbours:
            if atlas.path_exists(cluster.h3_hex_id, neighbour.h3_hex_id):
                continue

            path_node_ids = list(osmnx.distance.k_shortest_paths(
                graph,
                orig=cluster_centroid_graph_node_ids_by_hex_id[cluster.h3_hex_id],
                dest=cluster_centroid_graph_node_ids_by_hex_id[neighbour.h3_hex_id],
                k=1,
            ))[0]
            if len(path_node_ids) < 3:
                print("======")
                print(f"{cluster.h3_hex_id} to {neighbour.h3_hex_id}")
                print(path_node_ids)
                print("======")
                continue
            atlas.add_path(cluster.h3_hex_id, neighbour.h3_hex_id, path_node_ids)

    return atlas

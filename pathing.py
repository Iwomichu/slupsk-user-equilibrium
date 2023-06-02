from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

import h3
import networkx
import osmnx.distance

from clusters import Cluster
from types import NodeId, ClusterId
from distance import Speed, Distance


class PathAtlas:
    def __init__(self) -> None:
        self.path_from_cluster_id_to_cluster_id: Dict[ClusterId, Dict[ClusterId, List[NodeId]]] = defaultdict(dict)

    def add_path(self, from_cluster: ClusterId, to_cluster: ClusterId, path: List[NodeId]) -> None:
        self.path_from_cluster_id_to_cluster_id[from_cluster][to_cluster] = path

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
                continue
            atlas.add_path(cluster.h3_hex_id, neighbour.h3_hex_id, path_node_ids)

    return atlas


@dataclass(frozen=True)
class PathData:
    start_cluster: Cluster
    end_cluster: Cluster
    minimal_maximal_speed: Speed
    minimal_lane_count: int  # TODO: Maybe add more lane characteristics or stats
    length: Distance
    crosses_other_clusters: bool

    @property
    def max_capacity(self) -> int:
        return self.minimal_lane_count * 2200

    @property
    def free_flow_travel_time(self):
        return


def get_path_data(
        path: List[NodeId],
        graph: networkx.MultiDiGraph,
        resolution: int,
        clusters_by_cluster_id: Dict[ClusterId, Cluster],
) -> PathData:
    valid_clusters = set(clusters_by_cluster_id.keys())
    edge_details = [
        graph.get_edge_data(start, end)[0]  # TODO: Possibly multiple
        for start, end in zip(path, path[1:])
    ]
    clusters_crossed = [
        h3.geo_to_h3(graph.nodes[node]['y'], graph.nodes[node]['x'], resolution=resolution)
        for node in path
    ]
    valid_clusters_crossed = tuple(cluster_id for cluster_id in clusters_crossed if cluster_id in valid_clusters)
    total_meters = sum(details['length'] for details in edge_details)
    minimal_maximal_kph = min(details['speed_kph'] for details in edge_details)
    print(edge_details)
    minimal_lane_count = min(int(details.get('lanes', "1")[0]) for details in edge_details)
    crosses_other_clusters = (valid_clusters_crossed[0], valid_clusters_crossed[~0]) == valid_clusters_crossed
    return PathData(
        start_cluster=clusters_crossed[0],
        end_cluster=clusters_crossed[~0],
        minimal_maximal_speed=Speed(distance_per_hour=Distance(kilometers=minimal_maximal_kph)),
        minimal_lane_count=minimal_lane_count,
        length=Distance(meters=total_meters),
        crosses_other_clusters=crosses_other_clusters,
    )


def create_cluster_graph(graph: networkx.MultiDiGraph, clusters: List[Cluster], resolution: int) -> networkx.DiGraph:
    atlas = get_paths_between_clusters(graph, clusters)
    cluster_by_id = {cluster.h3_hex_id: cluster for cluster in clusters}
    edges = [
        (from_cluster, to_cluster, {"data": get_path_data(path, graph, resolution, cluster_by_id)})
        for from_cluster, destinations in atlas.path_from_cluster_id_to_cluster_id.items()
        for to_cluster, path in destinations.items()
    ]
    cluster_graph = networkx.DiGraph()
    cluster_graph.add_edges_from(edges)
    return cluster_graph

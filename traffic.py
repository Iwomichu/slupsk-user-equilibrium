from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict

import networkx

from clusters import Cluster
from distance import Time
from pathing import PathData, create_cluster_graph
from travel import Travel
from my_types import ClusterId
from utils import batched

TravelId = int


@dataclass
class Route:
    travel: Travel
    estimated_travel_time: Time
    nodes: List[ClusterId]


class TravelRouteAssigner(ABC):
    @abstractmethod
    def assign_routes(
            self,
            travels: List[Travel],
            clusters: List[Cluster],
            road_graph: networkx.MultiDiGraph,
    ) -> List[Route]:
        pass


@dataclass
class LinkState:
    path_data: PathData
    current_volume: List[TravelId] = field(default_factory=list)

    @property
    def travel_time(self) -> Time:
        minutes = self.path_data.free_flow_travel_time.minutes * \
            (1 + .15 * (len(self.current_volume) / self.path_data.max_capacity) ** 4)
        return Time(minutes=minutes)


class IncrementalBatchRouteAssigner(TravelRouteAssigner):
    def __init__(self, h3_resolution: int, batch_size: int = 200, iterations_count: int = 1) -> None:
        self.h3_resolution = h3_resolution
        self.batch_size = batch_size
        self.iterations_count = iterations_count
        self.graph = None

    def assign_routes(
            self,
            travels: List[Travel],
            clusters: List[Cluster],
            road_graph: networkx.MultiDiGraph,
    ) -> List[Route]:
        travel_by_id = {travel.id_: travel for travel in travels}
        self.graph = create_cluster_graph(road_graph, clusters, self.h3_resolution)
        for (start, end, data) in self.graph.edges.data("data"):
            state = LinkState(data)
            self.graph[start][end]["state"] = state
            self.graph[start][end]["weight"] = state.travel_time.minutes

        current_routes: Dict[TravelId, List[LinkState]] = {}
        for iteration in range(self.iterations_count):
            for travels_batch in batched(travels, self.batch_size):
                shortest_paths = dict(networkx.all_pairs_dijkstra_path(self.graph))
                for travel in travels_batch:
                    path = shortest_paths[travel.start.h3_hex_id][travel.end.h3_hex_id]
                    link_states = [self.graph[start][stop]["state"] for start, stop in zip(path, path[1:])]
                    for former_link_state in current_routes.get(travel.id_, []):
                        former_link_state.current_volume.remove(travel.id_)

                    current_routes[travel.id_] = link_states
                    for link_state in link_states:
                        link_state.current_volume.append(travel.id_)

                for (start, end, state) in self.graph.edges.data("state"):
                    self.graph[start][end]["weight"] = state.travel_time.minutes

        return [
            Route(
                travel=travel_by_id[travel_id],
                estimated_travel_time=Time(minutes=sum(link.travel_time.minutes for link in current_route)),
                nodes=[
                          link.path_data.start_cluster
                          for link in current_route
                      ] + [current_route[~0].path_data.end_cluster],
            )
            for travel_id, current_route in current_routes.items()
            if len(current_route) > 0
        ]

import random
from dataclasses import dataclass, field
from typing import List, Generator

from clusters import Cluster
from my_types import ClusterId
from population import PopulationGeneratorConfig


def id_generator() -> Generator[int, None, None]:
    i = 0
    while True:
        i += 1
        yield i


travel_id_generator = id_generator()


@dataclass
class Travel:
    start: Cluster
    end: Cluster
    id_: int = field(default_factory=lambda: next(travel_id_generator))


class TravelGenerator:
    def __init__(self, config: PopulationGeneratorConfig) -> None:
        self.config = config

    def generate_travels(self, clusters: List[Cluster]) -> List[Travel]:
        travels = []
        cluster_by_id = {cluster.h3_hex_id: cluster for cluster in clusters}
        cluster_weights = {cluster.h3_hex_id: len(cluster.points) for cluster in clusters}
        for cluster in clusters:
            travel_destinations: List[ClusterId] = random.choices(
                population=list(cluster_weights.keys()),
                weights=list(cluster_weights.values()),
                k=round(len(cluster.points) * self.config.travel_coefficient),
            )
            travels += [
                Travel(start=cluster_by_id[cluster.h3_hex_id], end=cluster_by_id[destination])
                for destination in travel_destinations
            ]
        return travels

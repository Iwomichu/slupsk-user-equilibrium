from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

import numpy as np

from distance import Distance, Coordinates
from types import PopulationGenerationDistributionKind


@dataclass
class PopulationGenerationEpicentre:
    label: str
    latitude: float
    longitude: float
    population_count: int
    radius: Distance
    distribution_kind: PopulationGenerationDistributionKind

    @staticmethod
    def from_json_record(record: dict[str, str]) -> PopulationGenerationEpicentre:
        return PopulationGenerationEpicentre(
            label=record['label'],
            latitude=float(record['latitude']),
            longitude=float(record['longitude']),
            population_count=int(record['population_count']),
            radius=Distance(meters=float(record['radius'])),
            distribution_kind=PopulationGenerationDistributionKind[record['distribution_kind'].upper()],
        )


@dataclass
class PopulationGeneratorConfig:
    epicentres: list[PopulationGenerationEpicentre]
    travel_coefficient: float

    @staticmethod
    def from_json_file(path: pathlib.Path) -> PopulationGeneratorConfig:
        with open(path, 'r') as f:
            config = json.load(f)
            return PopulationGeneratorConfig(
                epicentres=[
                    PopulationGenerationEpicentre.from_json_record(record) for record in config["epicentres"]
                ],
                travel_coefficient=config["travel_coefficient"],
            )


def generate_data_points(epicentre: PopulationGenerationEpicentre) -> list[Coordinates]:
    return [
        Coordinates(longitude=longitude, latitude=latitude)
        for longitude, latitude in np.random.normal(
            loc=(epicentre.longitude, epicentre.latitude),
            scale=(epicentre.radius.degrees, epicentre.radius.degrees),
            size=(epicentre.population_count, 2)
        )
    ]

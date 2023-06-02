from __future__ import annotations

from enum import Enum

NodeId = int
ClusterId = str


class ClusterCentreStrategy(str, Enum):
    MEAN = 'MEAN'
    HEXAGON_CENTER = 'HEXAGON_CENTER'


class PopulationGenerationDistributionKind(str, Enum):
    NORMAL = "NORMAL"

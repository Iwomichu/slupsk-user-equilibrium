import pathlib
from dataclasses import dataclass
from typing import List

import folium
import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns

from clusters import Cluster, ClusterCentreStrategy
from population import PopulationGeneratorConfig, generate_data_points
from traffic import IncrementalBatchRouteAssigner, Route, Time
from travel import TravelGenerator
from utils import visualize_clusters, visualize_points, visualize_weighted_paths, rescale


@dataclass
class SimulationResults:
    population_count: int
    cluster_graph: nx.MultiDiGraph
    routes: List[Route]
    mean_travel_time: Time
    clusters: List[Cluster]


def simulate(multiplier: float, resolution: int, cluster_centre_strategy: ClusterCentreStrategy,
             graph: nx.MultiDiGraph) -> SimulationResults:
    config = PopulationGeneratorConfig.from_json_file(pathlib.Path("configs/slupsk_2004.json"))
    config.multiply_population(multiplier)
    pts_by_epi = {epi.label: generate_data_points(epi) for epi in config.epicentres}
    points = [point for pts in pts_by_epi.values() for point in pts]
    clusters = Cluster.consolidate_clusters(Cluster.clusterize_points(points, resolution, cluster_centre_strategy),
                                            graph, resolution)
    travels = TravelGenerator(config).generate_travels(clusters)
    assigner = IncrementalBatchRouteAssigner(h3_resolution=8, iterations_count=4, batch_size=10)
    routes = assigner.assign_routes(travels, clusters, graph)
    mean_travel_time = sum([route.estimated_travel_time.minutes for route in routes]) / len(
        [route.estimated_travel_time.minutes for route in routes])
    return SimulationResults(len(points), assigner.graph, routes, mean_travel_time, clusters)


def create_df(results_list: List[SimulationResults]) -> pd.DataFrame:
    df = pd.DataFrame.from_dict({
        "population": [results.population_count for results in results_list],
        "mean_travel_times": [results.mean_travel_time for results in results_list]
    })
    df["log_mean_travel_time"] = np.log10(df["mean_travel_times"])
    df["log_population"] = np.log10(df["population"])
    return df


def create_line_plots(df: pd.DataFrame) -> ...:
    f = plt.figure(figsize=(12, 6))
    gs = f.add_gridspec(1, 2)
    ax = f.add_subplot(gs[0, 0])
    sns.lineplot(x="population", y="mean_travel_times", data=df, ax=ax)
    ax = f.add_subplot(gs[0, 1])
    sns.lineplot(x="population", y="log_mean_travel_time", data=df, ax=ax)
    return ax


def create_edges_df(cluster_graph: nx.MultiDiGraph) -> pd.DataFrame:
    edges_df = pd.DataFrame([
        {
            "start": start,
            "end": end,
            "travel_time": state.travel_time.minutes,
            "free_flow_travel_time": state.path_data.free_flow_travel_time.minutes,
            "capacity": state.path_data.max_capacity,
            "volume": len(state.current_volume),
            "path": state.path_data.path,
        } for (start, end, state) in cluster_graph.edges.data("state")
    ])

    edges_df["traffic_slowdown"] = edges_df["travel_time"] - edges_df["free_flow_travel_time"]
    return edges_df


def create_intercluster_travel_slowdown_graph(
        cluster_graph: nx.MultiDiGraph,
        clusters: List[Cluster],
) -> ...:
    edges_df = create_edges_df(cluster_graph)
    cluster_by_id = {cluster.h3_hex_id: cluster for cluster in clusters}
    pos = nx.planar_layout(cluster_graph, )

    nodelist = cluster_by_id.keys()
    cluster_pops = [len(cluster.points) for cluster in cluster_by_id.values()]
    node_sizes = [30 + 700 * np.log(1 + (pop_count - min(cluster_pops)) / (max(cluster_pops) - min(cluster_pops))) for
                  pop_count in cluster_pops]

    edge_volumes = [
        int(edges_df[(edges_df["start"] == start) & (edges_df["end"] == end)]["volume"])
        for (start, end) in cluster_graph.edges
    ]
    widths = [
        .5 + 10 * np.log(1 + (edge_volume - min(edge_volumes)) / (max(edge_volumes) - min(edge_volumes)))
        for edge_volume in edge_volumes
    ]

    edge_traffic_slowdowns = [
        int(edges_df[(edges_df["start"] == start) & (edges_df["end"] == end)]["traffic_slowdown"])
        for (start, end) in cluster_graph.edges
    ]
    edge_colors = edge_traffic_slowdowns
    cmap = plt.cm.copper_r
    f = plt.figure(figsize=(12, 6))
    ax = f.add_subplot()
    nodes = nx.draw_networkx_nodes(cluster_graph, pos, node_size=node_sizes, node_color="indigo", ax=ax)
    edges = nx.draw_networkx_edges(
        cluster_graph,
        pos,
        ax=ax,
        node_size=node_sizes,
        arrowstyle="->",
        arrowsize=5,
        edge_color=edge_colors,
        edge_cmap=cmap,
        width=widths,
    )

    pc = mpl.collections.PatchCollection(edges, cmap=cmap)
    pc.set_array(edge_colors)
    ax.set_axis_off()
    plt.colorbar(pc, ax=ax)
    return ax


def create_route_folium_map(
        cluster_graph: nx.MultiDiGraph,
        clusters: List[Cluster],
        graph: nx.MultiDiGraph,
        min_slowdown: int = 0,
        max_slowdown: int = 30,
        min_volume: int = 0,
        max_volume: int = 20000,
) -> ...:
    edges_df = create_edges_df(cluster_graph)
    cmap = plt.cm.copper_r
    edge_traffic_slowdowns = [
        round(row["traffic_slowdown"])
        for _, row in edges_df.iterrows()
    ]
    max_slowdown = max(max_slowdown, max(edge_traffic_slowdowns))
    colors = [
        mpl.colors.rgb2hex(cmap(rescale(slowdown, old_max=max_slowdown, old_min=min_slowdown, new_max=1, new_min=0)))
        for slowdown in edge_traffic_slowdowns
    ]
    edge_volumes = [
        round(row["volume"])
        for _, row in edges_df.iterrows()
    ]
    max_volume = max(max_volume, max(edge_volumes))
    weights = [
        rescale(volume, old_max=max_volume, old_min=min_volume, new_max=10, new_min=1)
        for volume in edge_volumes
    ]
    m = folium.Map(location=[54.46270136314862, 17.019373399360482], zoom_start=13, tiles='cartodbpositron')
    visualize_weighted_paths(m, graph, list(edges_df.path), colors, weights)
    visualize_clusters(m, clusters, ['green'])
    visualize_points(m, [cluster.centre for cluster in clusters], ['green'])
    return m

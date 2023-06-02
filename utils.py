from typing import List, Optional

import folium
import h3
import networkx
import osmnx
import osmnx.distance
from networkx.classes.reportviews import NodeView

from clusters import Cluster
from distance import Coordinates


def visualize_paths(
        map_: folium.Map,
        graph: networkx.MultiDiGraph,
        paths: List[List[NodeView]],
        colors: Optional[str] = None,
) -> None:
    if colors is None:
        colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen',
                  'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']

    for i, path in enumerate(paths):
        osmnx.plot_route_folium(graph, path, route_map=map_, color=colors[i % len(colors)])


def visualize_paths_coordinates(
        map_: folium.Map,
        graph: networkx.MultiDiGraph,
        paths: List[List[Coordinates]],
        colors: Optional[str] = None,
) -> None:
    visualize_paths(
        map_=map_,
        graph=graph,
        paths=[
            [osmnx.distance.nearest_nodes(graph, cords.longitude, cords.latitude) for cords in path] for path in paths
        ],
        colors=colors,
    )


def visualize_points(
        map_: folium.Map,
        points: List[Coordinates],
        colors: Optional[str] = None,
) -> None:
    if colors is None:
        colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen',
                  'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
    for i, point in enumerate(points):
        map_.add_child(
            folium.CircleMarker(
                location=(point.latitude, point.longitude),
                radius=0.2,
                color=colors[i % len(colors)],
                fill=True,
            ),
        )


def visualize_clusters(
        map_: folium.Map,
        clusters: List[Cluster],
        colors: Optional[str] = None,
) -> None:
    if colors is None:
        colors = ['blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 'darkblue', 'darkgreen',
                  'cadetblue', 'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen', 'gray', 'black', 'lightgray']
    hexagons = [cluster.h3_hex_id for cluster in clusters]
    polylines = []
    lat = []
    lng = []
    for hexagon in hexagons:
        polygons = h3.h3_set_to_multi_polygon([hexagon], geo_json=False)
        # flatten polygons into loops.
        outlines = [loop for polygon in polygons for loop in polygon]
        polyline = [outline + [outline[0]] for outline in outlines][0]
        lat.extend(map(lambda v: v[0], polyline))
        lng.extend(map(lambda v: v[1], polyline))
        polylines.append(polyline)

    for i, polyline in enumerate(polylines):
        poly_line = folium.PolyLine(
            locations=polyline,
            weight=1,
            color=colors[i % len(colors)],
            fill=True,
            tooltip=f"{len(clusters[i].points)}",
            popup=hexagons[i]
        )
        map_.add_child(poly_line)

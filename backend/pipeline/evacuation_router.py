import networkx as nx
from typing import List, Dict, Optional, Tuple

# Nearest exit for each zone
ZONE_NEAREST_EXIT = {
    "Main Hall":   "Stairwell A",
    "Corridor":    "Entrance",
    "Entrance":    "Emergency Exit North",
    "Exit Area":   "Emergency Exit South",
    "Stairwell A": "Emergency Exit North",
    "Stairwell B": "Emergency Exit South",
}

# Predefined building graph
BUILDING_NODES = [
    "Main Hall",
    "Corridor",
    "Entrance",
    "Exit Area",
    "Stairwell A",
    "Stairwell B",
    "Emergency Exit North",
    "Emergency Exit South",
    "Assembly Point",
]

BUILDING_EDGES = [
    # (from, to, weight)
    ("Main Hall", "Corridor", 2),
    ("Main Hall", "Stairwell A", 3),
    ("Main Hall", "Stairwell B", 3),
    ("Corridor", "Entrance", 2),
    ("Corridor", "Exit Area", 2),
    ("Corridor", "Stairwell A", 2),
    ("Entrance", "Emergency Exit North", 1),
    ("Exit Area", "Emergency Exit South", 1),
    ("Stairwell A", "Emergency Exit North", 2),
    ("Stairwell B", "Emergency Exit South", 2),
    ("Emergency Exit North", "Assembly Point", 1),
    ("Emergency Exit South", "Assembly Point", 1),
]

# Node positions for visualization (normalized 0-1)
NODE_POSITIONS = {
    "Main Hall":            (0.5, 0.5),
    "Corridor":             (0.5, 0.35),
    "Entrance":             (0.25, 0.2),
    "Exit Area":            (0.75, 0.2),
    "Stairwell A":          (0.2, 0.5),
    "Stairwell B":          (0.8, 0.5),
    "Emergency Exit North": (0.1, 0.1),
    "Emergency Exit South": (0.9, 0.1),
    "Assembly Point":       (0.5, 0.05),
}


class EvacuationRouter:
    def __init__(self):
        self.graph = nx.Graph()
        self.graph.add_nodes_from(BUILDING_NODES)
        for src, dst, w in BUILDING_EDGES:
            self.graph.add_edge(src, dst, weight=w)
        self._evacuation_route: Optional[List[str]] = None
        self._active = False

    def compute_route(self, high_risk_zones: List[str], start_zone: str) -> Optional[List[str]]:
        G = self.graph.copy()

        # Completely remove edges through CRITICAL zones
        for zone in high_risk_zones:
            if zone in G:
                # Remove all edges to/from high risk zones
                edges_to_remove = list(G.edges(zone))
                for edge in edges_to_remove:
                    if G.has_edge(*edge):
                        G.remove_edge(*edge)

        target = "Assembly Point"

        # Try from start zone first
        try:
            path = nx.dijkstra_path(G, start_zone, target, weight='weight')
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        # Try all non-critical nodes as starting points
        for node in BUILDING_NODES:
            if node not in high_risk_zones and node != target:
                try:
                    path = nx.dijkstra_path(G, node, target, weight='weight')
                    return path
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue

        # Last resort — use original graph with heavy penalties
        G2 = self.graph.copy()
        for zone in high_risk_zones:
            if zone in G2:
                for nb in list(G2.neighbors(zone)):
                    G2[zone][nb]['weight'] += 999
        try:
            return nx.dijkstra_path(G2, start_zone, target, weight='weight')
        except Exception:
            return None

    def activate_evacuation(self, high_risk_zones: List[str], start_zone: str = "Main Hall"):
        route = self.compute_route(high_risk_zones, start_zone)
        self._evacuation_route = route
        self._active = True
        return route

    def deactivate(self):
        self._active = False
        self._evacuation_route = None

    def get_route(self) -> Optional[List[str]]:
        return self._evacuation_route if self._active else None

    def get_graph_data(self, critical_zones: list = None) -> Dict:
        nodes = [{"id": n, "x": NODE_POSITIONS[n][0], "y": NODE_POSITIONS[n][1]}
                 for n in self.graph.nodes]
        edges = [{"from": u, "to": v, "weight": d["weight"]}
                 for u, v, d in self.graph.edges(data=True)]

        # support both _route and _evacuation_route attribute names
        route = getattr(self, '_route', None) or getattr(self, '_evacuation_route', None) or []

        nearest_exits = []
        if critical_zones:
            for zone in critical_zones:
                nearest = ZONE_NEAREST_EXIT.get(zone)
                if nearest:
                    nearest_exits.append({
                        "zone": zone,
                        "exit": nearest,
                    })

        return {
            "nodes": nodes,
            "edges": edges,
            "evacuation_route": route,
            "active": self._active,
            "nearest_exits": nearest_exits,
        }
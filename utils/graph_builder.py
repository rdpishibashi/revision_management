"""
Common graph building logic shared between Graphviz and Pyvis renderers
"""

import unicodedata
from collections import defaultdict


def normalize_parent_value(value):
    """
    Normalize a Parent-column value, converting placeholder strings that mean
    "no parent" (e.g. "None", case-insensitive) into an empty string so the
    drawing is treated as an independent node instead of being attached to a
    shared "None" node.

    Args:
        value: Raw Parent-column value (already converted to str)

    Returns:
        str: '' if the value is a "no parent" placeholder, otherwise the
             original value unchanged
    """
    if value.strip().lower() == 'none':
        return ''
    return value


def compute_edge_curvature(edges):
    """
    Assign per-edge curvature (vis-network 'smooth' options) so multiple edges
    that share the same source node fan out visually instead of overlapping.
    This matters when their target nodes happen to line up in a single
    vertical chain — e.g. a RevUp chain (34A->34B->34C->34D) that also all
    share a common 流用 parent (26D->34A, 26D->34B, 26D->34C, 26D->34D):
    without this, the "skip" edges (26D->34B, 26D->34C, ...) sit directly on
    top of each other. Edges alternate curve direction (clockwise /
    counter-clockwise) and increase roundness for each additional edge from
    the same source, fanning them out left/right around that source.

    Args:
        edges: List of (parent, child, is_dashed) tuples, as returned by
               GraphBuilder.get_edges()

    Returns:
        list: List of (parent, child, is_dashed, smooth_options) tuples,
              where smooth_options is a dict for vis-network's edge 'smooth' option
    """
    edge_index_by_source = defaultdict(int)
    result = []
    for parent, child, is_dashed in edges:
        idx = edge_index_by_source[parent]
        edge_index_by_source[parent] += 1
        curve_type = 'curvedCW' if idx % 2 == 0 else 'curvedCCW'
        roundness = min(0.15 + 0.12 * (idx // 2), 0.6)
        smooth_options = {'enabled': True, 'type': curve_type, 'roundness': roundness}
        result.append((parent, child, is_dashed, smooth_options))
    return result


def find_search_component_nodes(all_nodes, edges, query):
    """
    Determine which nodes to keep when filtering the graph by a drawing-number
    search box: nodes matching the query (partial match, NFKC-normalized,
    case-insensitive) plus every node reachable from them via any edge
    (explicit or inferred RevUp, direction ignored) — i.e. their full
    connected component(s).

    Args:
        all_nodes: Iterable of all node IDs in the graph
        edges: List of (parent, child, is_dashed) tuples, as returned by
               GraphBuilder.get_edges()
        query: Search string entered by the user (drawing number, or part of one)

    Returns:
        set: Node IDs to keep. If query is blank, returns all_nodes unchanged
             (no filtering). If query is non-blank but nothing matches,
             returns an empty set.
    """
    normalized_query = unicodedata.normalize('NFKC', query).strip().upper()
    if not normalized_query:
        return set(all_nodes)

    matched_nodes = {
        node for node in all_nodes
        if normalized_query in unicodedata.normalize('NFKC', node).upper()
    }
    if not matched_nodes:
        return set()

    adjacency = defaultdict(set)
    for parent, child, _ in edges:
        adjacency[parent].add(child)
        adjacency[child].add(parent)

    keep = set()
    for start in matched_nodes:
        if start in keep:
            continue
        stack = [start]
        while stack:
            node = stack.pop()
            if node in keep:
                continue
            keep.add(node)
            stack.extend(adjacency[node] - keep)
    return keep


class GraphBuilder:
    """
    Builds graph data structures from parent-child relationship data

    This class extracts common logic for processing node details, identifying
    root nodes, and preparing data for graph visualization.
    """

    NODE_FILL_COLOR = '#F0F8FF'  # AliceBlue (default)
    RELATION_REUSE_COLOR = '#FFFFE0'  # LightYellow (for 流用)

    def __init__(self, data, dynamic_cols_for_display):
        """
        Initialize GraphBuilder

        Args:
            data: pandas DataFrame with Child and Parent columns
            dynamic_cols_for_display: List of column names to display (excluding Child/Parent)
        """
        self.data = data
        self.dynamic_cols = dynamic_cols_for_display
        self.node_dynamic_details = {}
        self.all_children = set()
        self.all_parents = set()
        self.root_nodes = set()

    def build(self):
        """
        Build complete graph data structure

        Returns:
            tuple: (node_dynamic_details dict, root_nodes set)
        """
        self._collect_nodes()
        self._identify_root_nodes()
        self._build_node_details()
        self._set_root_node_attributes()
        return self.node_dynamic_details, self.root_nodes

    def _collect_nodes(self):
        """First pass: collect all children and parents"""
        for index, row in self.data.iterrows():
            child = str(row['Child']).strip()
            parent = str(row['Parent']).strip()

            if child:
                self.all_children.add(child)
            if parent:
                self.all_parents.add(parent)

    def _identify_root_nodes(self):
        """Identify root nodes (parents that are never children)"""
        self.root_nodes = self.all_parents - self.all_children

    def _build_node_details(self):
        """Second pass: build node details with attributes"""
        for index, row in self.data.iterrows():
            child = str(row['Child']).strip()
            parent = str(row['Parent']).strip()

            # Extract current node's attributes
            current_node_details = {}
            for col in self.dynamic_cols:
                current_node_details[col] = str(row[col]).strip()

            # Set Child attributes (Child record's attributes are used)
            if child:
                if child not in self.node_dynamic_details:
                    self.node_dynamic_details[child] = {}
                self.node_dynamic_details[child].update(current_node_details)

            # Register Parent if it exists (attributes set later)
            if parent:
                if parent not in self.node_dynamic_details:
                    self.node_dynamic_details[parent] = {}

    def _set_root_node_attributes(self):
        """Set special attributes for root nodes"""
        for root_node in self.root_nodes:
            if root_node in self.node_dynamic_details:
                self.node_dynamic_details[root_node] = {
                    'Relation': 'ROOT'
                }

    def get_node_color(self, details):
        """
        Determine node color based on Relation attribute

        Args:
            details: Dictionary of node attributes

        Returns:
            str: Hex color code
        """
        if 'Relation' in details and details['Relation'] == '流用':
            return self.RELATION_REUSE_COLOR
        return self.NODE_FILL_COLOR

    def get_edges(self):
        """
        Extract all parent-child edges: edges explicitly recorded in the ledger
        (solid), plus inferred RevUp edges for same-base, ascending-revision-letter
        node pairs that have no explicit row connecting them (dashed).

        Returns:
            list: List of (parent, child, is_dashed) tuples
        """
        edges = []
        explicit_pairs = set()
        for index, row in self.data.iterrows():
            child = str(row['Child']).strip()
            parent = str(row['Parent']).strip()
            if parent and child:
                edges.append((parent, child, False))
                explicit_pairs.add((parent, child))

        for parent, child in self._infer_revision_up_edges(explicit_pairs):
            edges.append((parent, child, True))

        return edges

    def _infer_revision_up_edges(self, explicit_pairs):
        """
        Infer RevUp edges between nodes that share the same base drawing number
        (identical except for the trailing revision letter) but have no explicit
        row connecting them in the ledger. Only adjacent revisions among the
        nodes that actually exist in the graph are connected (e.g. among A, C, D
        existing as nodes: A-C and C-D, not A-D), forming a chain per base.

        Args:
            explicit_pairs: Set of (parent, child) tuples already recorded in the ledger

        Returns:
            list: List of (parent, child) tuples for inferred RevUp edges
        """
        groups = defaultdict(list)
        for node in (self.all_children | self.all_parents):
            if len(node) >= 2 and node[-1].isalpha():
                groups[node[:-1]].append(node)

        inferred = []
        for base, members in groups.items():
            if len(members) < 2:
                continue
            members = sorted(members, key=lambda n: n[-1].upper())
            for earlier, later in zip(members, members[1:]):
                if (earlier, later) not in explicit_pairs:
                    inferred.append((earlier, later))
        return inferred

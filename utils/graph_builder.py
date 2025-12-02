"""
Common graph building logic shared between Graphviz and Pyvis renderers
"""


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
        Extract all parent-child edges from data

        Returns:
            list: List of (parent, child) tuples
        """
        edges = []
        for index, row in self.data.iterrows():
            child = str(row['Child']).strip()
            parent = str(row['Parent']).strip()
            if parent and child:
                edges.append((parent, child))
        return edges

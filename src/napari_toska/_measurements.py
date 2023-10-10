import pandas as pd


def analyze_skeletons(
        labeled_skeletons: "napari.types.LabelsData",
        parsed_skeletons: "napari.types.LabelsData",
        neighborhood: str = "n8",
        viewer: "napari.Viewer" = None
        ) -> pd.DataFrame:
    import numpy as np

    for label in np.unique(labeled_skeletons)[1:]:
        parsed_skeletons_single = parsed_skeletons * (labeled_skeletons == label)
        df = analyze_single_skeleton(
            parsed_skeletons_single, neighborhood=neighborhood)
        df["skeleton_id"] = label
        if label == 1:
            df_all = df
        else:
            df_all = pd.concat([df_all, df], axis=0)

    # move skeleton id to first column by its name
    col = df_all.pop('skeleton_id')  # Remove column 'B' and store it in col
    df_all.insert(0, 'skeleton_id', col)

    # add label column
    df_all["label"] = df_all["skeleton_id"].values

    if viewer is not None:
        from napari_workflows._workflow import _get_layer_from_data
        from napari_skimage_regionprops import add_table
        skeleton_layer = _get_layer_from_data(viewer, labeled_skeletons)
        skeleton_layer.features = df_all
        add_table(skeleton_layer, viewer)

    return df_all


def analyze_single_skeleton(
        parsed_skeleton: "napari.types.LabelsData",
        neighborhood: str = "n8"
        ) -> pd.DataFrame:
    import networkx as nx
    import numpy as np
    from ._network_analysis import (
        create_adjacency_matrix,
        convert_adjacency_matrix_to_graph)
    from ._backend_toska_functions import skeleton_spine_search

    # create an adjacency matrix for the skeleton
    adjacency_matrix = create_adjacency_matrix(parsed_skeleton,
                                               neighborhood=neighborhood)
    graph = convert_adjacency_matrix_to_graph(adjacency_matrix)

    # number of end points
    n_endpoints = sum(adjacency_matrix.sum(axis=1) == 1)

    # number of branch points
    n_branch_points = sum(adjacency_matrix.sum(axis=1) > 1)

    # number of nodes
    n_nodes = n_endpoints + n_branch_points

    # number of branches
    n_branches = adjacency_matrix.shape[1]

    # spine length
    _, spine_paths_length = skeleton_spine_search(
        adjacency_matrix, graph)
    spine_length = np.nansum(spine_paths_length)

    # cycle basis
    directed_graph = graph.to_directed()
    possible_directed_cycles = list(nx.simple_cycles(directed_graph))

    n_cycle_basis = len(nx.cycle_basis(graph))
    n_possible_undirected_cycles = len(
        [x for x in possible_directed_cycles if len(x) > 2])//2

    df = pd.DataFrame(
        {
            "n_endpoints": [n_endpoints],
            "n_branch_points": [n_branch_points],
            "n_nodes": [n_nodes],
            "n_branches": [n_branches],
            "spine_length": [spine_length],
            "n_cycle_basis": [n_cycle_basis],
            "n_possible_undirected_cycles": [n_possible_undirected_cycles]
        }
    )

    return df


def analyze_single_skeleton_network(
        parsed_skeleton_single: "napari.types.LabelsData",
        neighborhood: str = "n8"
) -> pd.DataFrame:
    import networkx as nx
    import numpy as np
    from skimage import measure
    import pandas as pd
    from ._network_analysis import (
        create_adjacency_matrix,
        convert_adjacency_matrix_to_graph)
    from ._backend_toska_functions import skeleton_spine_search

    # create an adjacency matrix for the skeleton
    adjacency_matrix = create_adjacency_matrix(parsed_skeleton_single,
                                               neighborhood=neighborhood)
    graph = convert_adjacency_matrix_to_graph(adjacency_matrix)

    # get edge and node labels
    node_labels = np.arange(1, adjacency_matrix.shape[0]+1)
    edge_labels = np.arange(1, adjacency_matrix.shape[1]+1)

    # component type
    component_type = ['node'] * adjacency_matrix.shape[0] +\
        ['edge'] * adjacency_matrix.shape[1]

    # Assemble the table
    features = pd.DataFrame(
        {
            "label": np.arange(1, np.amax(node_labels) + np.amax(edge_labels) +1),
            "component_type": component_type
        }
    )

    # Measurement: Node degree
    node_degrees = adjacency_matrix.sum(axis=1)
    features.loc[features["component_type"] == "node", "degree"] = node_degrees

    # add all edge weights to dataframe
    edge_weights = nx.get_edge_attributes(graph, "weight")
    features.loc[features["component_type"] == "edge", "weight"] = list(edge_weights.values())
    features.loc[features["component_type"] == "edge", "node_1"] = np.asarray(graph.edges)[:, 0]
    features.loc[features["component_type"] == "edge", "node_2"] = np.asarray(graph.edges)[:, 1]
    features.loc[features["component_type"] == "node", "node_labels"] = list(graph.nodes)

    return features

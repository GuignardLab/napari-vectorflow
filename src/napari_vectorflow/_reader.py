"""
This module is an example of a barebones numpy reader plugin for napari.

It implements the Reader specification, but your plugin may choose to
implement multiple readers or even other plugin contributions. see:
https://napari.org/stable/plugins/guides.html?#readers
"""
import numpy as np
from itertools import product
from tifffile import imread
from pathlib import Path


def napari_get_reader(path):
    """A basic implementation of a Reader contribution.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    function or None
        If the path is a recognized format, return a function that accepts the
        same path or list of paths, and returns a list of layer data tuples.
    """
    if isinstance(path, list):
        # reader plugins may be handed single path, or a list of paths.
        # if it is a list, it is assumed to be an image stack...
        # so we are only going to look at the first file.
        path = path[0]
    elif Path(path).is_dir():
        return reader_function

    # if we know we cannot read the file, we immediately return None.
    if not path.endswith(".tif") and not path.endswith(".tiff"):
        return None

    # otherwise we return the *function* that can read ``path``.
    return reader_function


def reader_function(path):
    """Take a path or list of paths and return a list of LayerData tuples.

    Readers are expected to return data as a list of tuples, where each tuple
    is (data, [add_kwargs, [layer_type]]), "add_kwargs" and "layer_type" are
    both optional.

    Parameters
    ----------
    path : str or list of str
        Path to file, or list of paths.

    Returns
    -------
    layer_data : list of tuples
        A list of LayerData tuples where each tuple in the list contains
        (data, metadata, layer_type), where data is a numpy array, metadata is
        a dict of keyword arguments for the corresponding viewer.add_* method
        in napari, and layer_type is a lower-case string naming the type of
        layer. Both "meta", and "layer_type" are optional. napari will
        default to layer_type=="image" if not provided
    """
    # handle both a string and a list of strings
    if isinstance(path, str) and not Path(path).is_dir():
        paths = [path]
    elif Path(path).is_dir():
        paths = [p for p in Path(path).iterdir() if p.suffix in ['.tif', '.tiff']]
    else:
        return
    # # load all files into array
    # arrays = [imread(_path) for _path in paths]
    # # stack arrays into single array
    # data = np.squeeze(np.stack(arrays))

    # optional kwargs for the corresponding viewer.add_* method
    add_kwargs = {}

    layer_type = "vectors"  # optional, default is "image"
    all_vects = []
    all_lengths = []
    if 1<len(paths):
        for t, _path in enumerate(sorted(paths)):
            data = imread(_path)
            coord = np.array(list(product(np.arange(data.shape[0]), np.arange(data.shape[1]), np.arange(data.shape[2]))))
            coord = np.hstack([t+np.zeros(len(coord), dtype=coord.dtype).reshape(-1, 1), coord])
            vects = np.hstack(
                    (
                        coord,
                        np.zeros((len(coord), 1)),
                        data[coord[:, 1], coord[:, 2], coord[:, 3], 0].reshape(-1, 1),
                        data[coord[:, 1], coord[:, 2], coord[:, 3], 1].reshape(-1, 1), 
                        data[coord[:, 1], coord[:, 2], coord[:, 3], 2].reshape(-1, 1),
                    )
                )
            vects = vects.reshape(-1, 2, 4)
            all_vects.append(vects)
            all_lengths.append(np.linalg.norm(vects[:, 1], axis=1))
        all_vects = np.concatenate(all_vects)
        all_lengths = np.concatenate(all_lengths)
    else:
        data = imread(paths[0])
        coord = np.array(list(product(np.arange(data.shape[0]), np.arange(data.shape[1]), np.arange(data.shape[2]))))
        vects = np.hstack(
                (
                    coord,
                    data[coord[:, 0], coord[:, 1], coord[:, 2], 0].reshape(-1, 1),
                    data[coord[:, 0], coord[:, 1], coord[:, 2], 1].reshape(-1, 1), 
                    data[coord[:, 0], coord[:, 1], coord[:, 2], 2].reshape(-1, 1),
                )
            )
        all_vects = vects.reshape(-1, 2, 3)
        all_lengths = np.linalg.norm(all_vects[:, 1], axis=1)
    features = {
        "length": all_lengths,
    }
    metadata = {
        # Here we assume that all VF have the same shape
        "shape": ((len(paths), ) if 1<len(paths) else ()) + data.shape,
        "init_length": all_lengths,
        "init_data": all_vects.copy()
    }
    add_kwargs = {
        'edge_width': .1,
        'features': features, 
        'metadata': metadata,
        'edge_colormap': 'viridis',
        'edge_color': 'length'
    }
    return [(all_vects, add_kwargs, layer_type)]

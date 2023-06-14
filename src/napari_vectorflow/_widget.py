"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""
from typing import TYPE_CHECKING

from magicgui import widgets
from qtpy.QtWidgets import QVBoxLayout, QComboBox, QWidget
from qtpy.QtCore import QStringListModel
import numpy as np

if TYPE_CHECKING:
    import napari


class VectorFlowWidget(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def get_intensity_layers(self, *args):
        new_choices = [l.name for l in self.viewer.layers if l.as_layer_data_tuple()[-1] == 'image']
        self.model_choices['intensity'].setStringList(new_choices)
        return new_choices
    
    def get_vectors_layers(self, *args):
        new_choices = [l.name for l in self.viewer.layers if l.as_layer_data_tuple()[-1] == 'vectors']
        self.model_choices['vectors'].setStringList(new_choices)
        return new_choices

    def get_layers(self, *args):
        new_choices = [l.name for l in self.viewer.layers if l.as_layer_data_tuple()[-1] == 'image']
        self.model_choices['intensity'].setStringList(new_choices)
        new_choices = [l.name for l in self.viewer.layers if l.as_layer_data_tuple()[-1] == 'vectors']
        self.model_choices['vectors'].setStringList(new_choices)

    def threshold_from_image(self):
        for l in self.viewer.layers:
            if l.name == self.intensity_cbox.currentText():
                data_int = l.data
                layer_int = l
                if not isinstance(data_int, np.ndarray):
                    first_tp = np.array(data_int[0]).shape
                    if not all([first_tp==np.array(data_int[i]).shape for i in range(data_int.shape[0])]):
                        print('All intensity images have to have the same shape across time.')
                    else:
                        data_int = np.array(data_int)
            if l.name == self.vectors_cbox.currentText():
                data_vect = l.data
                layer_vect = l
        th_val = self.threshold_value.value
        shape_vect = layer_vect.metadata['shape']
        shape_int = data_int.shape
        min_dim = min(len(shape_int), len(shape_vect))
        shift = len(shape_vect) - 1 - min_dim
        slicing = tuple(slice(shape_vect[shift+i]) for i in range(min_dim))
        data_int = data_int[slicing]
        to_keep = np.where(th_val<data_int)
        # change = lambda z, y, x: ((shape_vect[1])*(shape_vect[2]))*coord[2] + (shape_vect[2])*coord[1] + coord[0]
        change = lambda coord: np.sum([(coord[min_dim-1-i]*np.product(shape_vect[-1-i:-1])) for i in range(min_dim)], axis=0, dtype=int)
        pos_to_keep = change(to_keep)
        data_subset = layer_vect.metadata['init_data'][pos_to_keep]
        features_subset = layer_vect.metadata['init_length'][pos_to_keep]
        layer_vect.data = data_subset
        layer_vect.features['length'] = features_subset
        layer_vect.edge_color = 'length'
        layer_vect.refresh()


    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        # Choice of intensity image and vectorfield
        self.model_choices = {
            'intensity': QStringListModel(),
            'vectors': QStringListModel()
        }

        self.get_layers()

        name_int_cbox = widgets.Label(value='Intensity Image:')
        self.intensity_cbox = QComboBox()
        self.intensity_cbox.setModel(self.model_choices['intensity'])
        self.intensity_cbox.native = self.intensity_cbox
        
        name_vf_cbox = widgets.Label(value='Vectorfield:')
        self.vectors_cbox = QComboBox()
        self.vectors_cbox.setModel(self.model_choices['vectors'])
        self.vectors_cbox.native = self.vectors_cbox
        
        self.data_selection = widgets.Container(
            widgets=[
                name_int_cbox,
                self.intensity_cbox,
                name_vf_cbox,
                self.vectors_cbox,
            ],
            labels=False
        )

        self.viewer.layers.events.inserted.connect(self.get_layers)
        self.viewer.layers.events.removed.connect(self.get_layers)

        # Thresholding from the image
        label_threshold = widgets.Label(value='Thresholding from\nintensity image')
        self.threshold_value = widgets.Slider(value=0, min=0, max=255)
        self.button_threhold = widgets.PushButton(text='Threshold!')
        self.button_threhold.clicked.connect(self.threshold_from_image)
        self.threshold_from_image_widget = widgets.Container(
            widgets=[
                label_threshold,
                self.threshold_value,
                self.button_threhold
            ],
            labels=False
        )

        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.setSpacing(0)
        self.setLayout(layout)

        self.layout().addWidget(self.data_selection.native)
        self.layout().addWidget(self.threshold_from_image_widget.native)


    def _on_click(self):
        print("napari has", len(self.viewer.layers), "layers")
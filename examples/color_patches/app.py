"""Handles the definition of the canvas parameters and
the drawing of the model representation on the canvas.
"""

from color_patches.model import ColorPatches
from mesa.visualization import (
    SolaraViz,
    make_space_component,
)

_COLORS = [
    "Aqua",
    "Blue",
    "Fuchsia",
    "Gray",
    "Green",
    "Lime",
    "Maroon",
    "Navy",
    "Olive",
    "Orange",
    "Purple",
    "Red",
    "Silver",
    "Teal",
    "White",
    "Yellow",
]


grid_rows = 50
grid_cols = 25
cell_size = 10
canvas_width = grid_rows * cell_size
canvas_height = grid_cols * cell_size


def color_patch_draw(cell):
    """Portrayal function called each tick to describe how to draw a cell.

    Reads the opinion state from model.opinion_grid rather than from an agent
    attribute, because state now lives on the model as a NumPy array.

    :param cell: the cell in the simulation
    :return: the portrayal dictionary
    """
    if cell is None:
        raise AssertionError

    # Retrieve the ColorCell agent sitting on this grid position.
    agent = cell.agents[0] if cell.agents else None
    model = agent.model if agent else None

    x, y = cell.coordinate
    # Look up the opinion state from the model-level NumPy array.
    state = int(model.opinion_grid[x, y]) if model else 0

    return {
        "Shape": "rect",
        "w": 1,
        "h": 1,
        "Filled": "true",
        "Layer": 0,
        "x": x,
        "y": y,
        "color": _COLORS[state],
    }


space_component = make_space_component(
    color_patch_draw,
    draw_grid=False,
)
model = ColorPatches()
page = SolaraViz(
    model,
    components=[space_component],
    model_params={"width": grid_rows, "height": grid_cols},
    name="Color Patches",
)

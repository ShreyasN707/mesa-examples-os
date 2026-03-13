"""
The model - a 2D lattice where agents live and have an opinion.

Environment state (the cell opinions) is stored in model.opinion_grid as a
NumPy array instead of inside individual ColorCell agents. This follows the
pattern from Issue #366: patch agents that only hold environment state are
replaced by a grid-level array on the model.

ColorCell agents are kept as lightweight wrappers for visualization.
"""

from collections import Counter

import numpy as np
import mesa
from mesa.discrete_space import FixedAgent
from mesa.discrete_space.grid import OrthogonalMooreGrid


class ColorCell(FixedAgent):
    """Lightweight visualization wrapper.

    The actual opinion state is stored in model.opinion_grid as a NumPy array.
    This agent exists only so the Solara visualization can iterate over cell
    positions and read state from the model.
    """

    # The 16 possible opinion values, kept as a class constant for reference.
    OPINIONS = list(range(16))

    def __init__(self, cell, model):
        """Place a visualization marker at the given grid cell."""
        super().__init__(model)
        self.cell = cell


class ColorPatches(mesa.Model):
    """
    Represents a 2D lattice where cells vote toward the majority opinion of
    their neighbors. Opinion state lives in model.opinion_grid (NumPy array)
    rather than inside agent objects.
    """

    def __init__(self, width=20, height=20):
        """
        Create a 2D lattice with strict borders where agents live.
        The agents next state is first determined before updating the grid.
        """
        super().__init__()

        self._grid = OrthogonalMooreGrid(
            (width, height), torus=False, random=self.random
        )

        # Opinion state stored as a NumPy array: values 0-15 map to 16 colors.
        self.opinion_grid = self.rng.integers(0, 16, size=(width, height), dtype=np.int8)

        # Create a lightweight ColorCell agent at each position for visualization.
        for cell in self._grid.all_cells:
            ColorCell(cell, self)

        self.running = True

    def step(self):
        """
        Update all cell opinions simultaneously.

        Each cell adopts the most common opinion among its 8 neighbors. Ties
        are broken randomly. A new_opinion array is computed from the current
        state before any values are written, so all cells read from the same
        snapshot (matching the original two-phase determine/assume design).
        """
        new_opinion = self.opinion_grid.copy()

        for agent in self.agents:
            x, y = agent.cell.coordinate

            # Count how many neighbors hold each opinion value.
            neighbor_counts = Counter(
                self.opinion_grid[nx, ny]
                for n in agent.cell.neighborhood
                for nx, ny in [n.coordinate]
            )

            polled = neighbor_counts.most_common()
            if not polled:
                continue

            max_count = polled[0][1]

            # Collect all opinions that tie for the top count.
            tied = [opinion for opinion, count in polled if count == max_count]

            # Resolve the tie randomly (or just pick the single winner).
            new_opinion[x, y] = self.rng.choice(tied)

        self.opinion_grid = new_opinion

    @property
    def grid(self):
        """Expose _grid as grid for compatibility with Mesa visualization."""
        return self._grid

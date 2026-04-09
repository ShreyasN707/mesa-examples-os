import mesa

class MinipaperAgent(mesa.Agent):
    def step(self):
        pass

class MinipaperModel(mesa.Model):
    def __init__(self):
        super().__init__()
        # In mesa 3.x / 4.x, schedulers are deprecated, we can just use the agent list or simply pass.
        self.running = True

    def step(self):
        pass

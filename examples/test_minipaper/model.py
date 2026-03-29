import mesa


class TestAgent(mesa.Agent):
    def step(self):
        # agent-level logic here
        pass


class TestModel(mesa.Model):
    def __init__(self):
        super().__init__()
        for _ in range(10):
            self.agents.add(TestAgent(self))
        self.running = True

    def step(self):
        self.agents.shuffle_do("step")
        if self.steps >= 5:
            self.running = False

"""Base class for all skills."""


class Skill:
    name: str = ""
    description: str = ""
    parameters: dict = {}

    def schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def execute(self, evento, args):
        raise NotImplementedError

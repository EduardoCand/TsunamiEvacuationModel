from mesa_geo.visualization.ModularVisualization import ModularServer
from mesa.visualization.modules import ChartModule, TextElement
from mesa.visualization.UserParam import UserSettableParameter
from model import TsunamiModel, PersonAgent
from mesa_geo.visualization.MapModule import MapModule
from tsunami_model.agents import MarkerAgent, MapAgent, MarkerRoadAgent


class TsunamiText(TextElement):
    """
    Display a text count of how many steps have been taken
    """

    def __init__(self):
        pass

    def render(self, model):
        return "Steps: " + str(model.steps)


class ClockElement(TextElement):
    def __init__(self):
        super().__init__()
        pass

    def render(self, model):
        return f"Timer: {model.minute:02d}:{model.second:02d}"


model_params = {
    "pop_size": UserSettableParameter("number", "Population size", 1, 1, 1500, 1),
    "pop_child_size": UserSettableParameter("number", "Child population size", 1, 1, 1500, 1),
}


def tsunami_draw(agent):
    """
    Portrayal Method for canvas
    """
    portrayal = dict()
    if isinstance(agent, PersonAgent):
        portrayal["radius"] = "1"

    if isinstance(agent, MapAgent):
        if "pessoas" in agent.uniqueID:
            portrayal["color"] = "Black"
        elif "chapeus" in agent.uniqueID:
            portrayal["color"] = "Black"
        elif "passadiço" in agent.uniqueID:
            portrayal["color"] = "Grey"
        elif "escadas" in agent.uniqueID:
            portrayal["color"] = "Green"
        elif "edif" in agent.uniqueID:
            portrayal["color"] = "Orange"
        elif "edif" in agent.uniqueID:
            portrayal["color"] = "Orange"
        elif "parque_estac" in agent.uniqueID:
            portrayal["color"] = "Purple"
        elif "estrada" in agent.uniqueID:
            portrayal["color"] = "Black"
        elif "safe" in agent.uniqueID:
            portrayal["color"] = "Red"
        else:
            portrayal["color"] = "Red"

    if agent.atype in ["susceptible"]:
        portrayal["color"] = "Red"
    elif agent.atype in ["child_susceptible"]:
        portrayal["color"] = "LightBlue"
    elif agent.atype in ["child_off_beach"]:
        portrayal["color"] = "DarkBlue"
    elif agent.atype in ["safe"]:
        portrayal["color"] = "Green"
    elif agent.atype in ["off_beach"]:
        portrayal["color"] = "Orange"
    return portrayal


tsunami_text = TsunamiText()
map_element = MapModule(tsunami_draw, TsunamiModel.MAP_COORDS, 16, 800, 1200)
clock_element = ClockElement()
tsunami_chart = ChartModule(
    [
        {"Label": "safe", "Color": "Green"},
        {"Label": "susceptible", "Color": "Red"},
        {"Label": "child_susceptible", "Color": "LightBlue"},
        {"Label": "child_off_beach", "Color": "DarkBlue"},
        {"Label": "off_beach", "Color": "Orange"},
    ]
)

server = ModularServer(TsunamiModel, [map_element, clock_element, tsunami_text, tsunami_chart], "Figueirinha Beach Simulation",
                       model_params)
server.launch()

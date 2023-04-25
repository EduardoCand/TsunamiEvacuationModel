import math
import random
import numpy as np

from mesa_geo import GeoAgent
from shapely.geometry import Point


class PersonAgent(GeoAgent):
    """Person Agent."""

    def __init__(self, unique_id, model, shape, agent_type="susceptible"):
        """
        Create a new person agent.
        :param unique_id:   Unique identifier for the agent
        :param model:       Model in which the agent runs
        :param shape:       Shape object for the agent
        :param agent_type:  Indicator if agent is infected ("susceptible", "child_susceptible", "off_beach", "child_off_beach" or "safe")
        """
        super().__init__(unique_id, model, shape)
        # Agent parameters
        self.speed_old_child = 0
        self.normalized_vector = ()
        self.vector_size = 0
        self.movement_vector = 0
        self.atype = agent_type
        # self.speed = random.randint(97, 143)/100
        self.break_rules_percent = random.randint(1, 100)
        self.speed = np.random.normal(1.12, 0.17, 1)[0]
        self.speed_old = self.speed
        # self.break_rules_percent = 10
        # self.speed = 1
        self.speed_penalty = self.speed / 1.3
        self.speed_penalty_child = 0
        self.can_move = True
        self.target_marker = tuple()
        self.second_target_marker = tuple()
        self.start_position = tuple()
        self.moving_to_safety = False
        self.distance = 0
        self.marker_type = ""

    def get_break_rules_percent(self):
        return self.break_rules_percent

    def set_agent_speed(self, type):
        if type == "child_susceptible":
            #self.speed = random.randint(49, 129)/100
            self.speed = np.random.normal(1.0, 0.17, 1)[0]
            #self.speed = 0.50
            self.speed_penalty_child = self.speed / 1.3
            self.speed_old_child = self.speed

    def set_agent_type(self, type):
        self.atype = type

    def set_start_position(self, x, y):
        self.start_position = (x, y)

    def set_target_marker(self, marker):
        self.target_marker = marker

    def get_distance_to_target_marker(self):
        if self.target_marker == tuple():
            return 0
        return math.sqrt((self.shape.x - self.target_marker[0]) ** 2 + (self.shape.y - self.target_marker[1]) ** 2)

    def move_point(self, dx, dy):
        """
        Move a point by creating a new one
        :param dx:  Distance to move in x-axis
        :param dy:  Distance to move in y-axis
        """
        return Point(self.shape.x + dx, self.shape.y + dy)

    def step(self):
        """Advance one step."""

        self.is_on_sand()
        self.move()

        safe_area_agents = self.model.grid.get_intersecting_agents(self)
        for safe_area_agent in safe_area_agents:
            if "safe" in safe_area_agent.unique_id:
                self.atype = "safe"

        self.model.counts[self.atype] += 1  # Count agent type

    # Checks if agent is touching sand
    def is_on_sand(self):
        agents = self.model.grid.get_neighbors_within_distance(self, 5)
        for agent in agents:
            if not (agent.atype == "trail" or agent.atype == "marker_beach" or agent.atype == "marker_road" or agent.atype == "parking" or agent.atype == "street"):
                if self.atype == "child_susceptible" or self.atype == "child_off_beach":
                    self.speed = self.speed_penalty_child
                else:
                    self.speed = self.speed_penalty
            else:
                if self.atype == "child_susceptible" or self.atype == "child_off_beach":
                    self.speed = self.speed_old_child
                else:
                    self.speed = self.speed_old

    def is_touching(self):
        agents = self.model.grid.get_neighbors_within_distance(self, 3)
        for agent in agents:
            if (agent.atype == "susceptible" or agent.atype == "off_beach" or agent.atype == "child_susceptible" or agent.atype == "child_off_beach") and agent.unique_id != self.unique_id:
                return True

    def check_touch(self):
        agents_nearby = []
        agents = self.model.grid.get_neighbors_within_distance(self, 3)  # detect distance of agent
        correct_marker = self.target_marker

        self.can_move = True
        for agent in agents:
            if (
                    agent.atype == "susceptible" or agent.atype == "off_beach" or agent.atype == "child_susceptible" or agent.atype == "child_off_beach") and agent.unique_id != self.unique_id:
                agents_nearby.append(agent)
                if self.target_marker == agent.target_marker and self.is_touching():  # checks if going to same place plus if its touching another agent
                    if self.get_distance_to_target_marker() > agent.get_distance_to_target_marker():
                        self.can_move = False
                        if self.marker_type == "marker_road":
                            correct_marker = self.second_target_marker
                            self.can_move = True
                            #self.can_move = False
        return [self.can_move, correct_marker]

    def move(self):

        off_beach_agents = self.model.grid.get_intersecting_agents(self)
        marker_agents = self.model.grid.get_neighbors_within_distance(self, 15)

        if not self.moving_to_safety:
            self.marker_type = "marker_beach"
        else:
            self.marker_type = "marker_road"
        # If not in off_beach_area then move
        check_touch_result = self.check_touch()
        correct_target_marker = check_touch_result[1]
        if check_touch_result[0]:
            if self.atype == "susceptible" or self.atype == "off_beach" or self.atype == "child_susceptible" or self.atype == "child_off_beach":
                if self.target_marker != tuple():

                    self.movement_vector = (correct_target_marker[0] - self.shape.x, correct_target_marker[1] - self.shape.y)
                    self.vector_size = math.sqrt(self.movement_vector[0] ** 2 + self.movement_vector[1] ** 2)
                    self.normalized_vector = (self.movement_vector[0] / self.vector_size, self.movement_vector[1] / self.vector_size)
                    self.shape = self.move_point(self.speed * self.normalized_vector[0],self.speed * self.normalized_vector[1])
                    c_distance = math.sqrt((self.shape.x - correct_target_marker[0]) ** 2 + (self.shape.y - correct_target_marker[1]) ** 2)

                    if c_distance < 1:  # if agente on top of marker then search for the next marker
                        nearby_agents = self.model.grid.get_neighbors_within_distance(self, self.speed)
                        for agent in nearby_agents:
                            if agent.atype == self.marker_type:
                                self.start_position = (agent.shape.x, agent.shape.y)
                                self.target_marker = agent.get_next_marker()
                                self.target_marker_type = agent.atype
                                if agent.atype == "marker_road":
                                    self.second_target_marker = agent.get_second_next_marker()

                # after reaching off beach area
                distance_closest_marker = 1000
                if not self.moving_to_safety:

                    for off_beach_agent in off_beach_agents:
                        if "escadas" in off_beach_agent.unique_id:
                            if self.atype == "susceptible":
                                self.atype = "off_beach"
                            else:
                                self.atype = "child_off_beach"
                            for marker_agent in marker_agents:
                                if marker_agent.atype == "marker_road":
                                    self.distance = self.shape.distance(marker_agent.shape)
                                    if self.distance < distance_closest_marker:
                                        distance_closest_marker = self.distance
                                        self.target_marker = [marker_agent.shape.x, marker_agent.shape.y]
                                        self.second_target_marker = marker_agent.get_next_marker()
                            self.moving_to_safety = True
                            self.start_position = (self.shape.x, self.shape.y)



        else:
            return 0

    def __repr__(self):
        return "Person " + str(self.unique_id)


class MarkerAgent(GeoAgent):
    def __init__(self, unique_id, model, shape, agent_type="marker_beach"):
        super().__init__(unique_id, model, shape)
        self.atype = agent_type
        self.next_marker = tuple()
        self.distance_to_off_beach_area = 0

    def set_distance_to_off_beach_area(self, distance):
        self.distance_to_off_beach_area = distance

    def set_next_marker(self, next_marker):
        self.next_marker = next_marker

    def get_next_marker(self):
        return self.next_marker

    def get_distance(self):
        return self.distance_to_off_beach_area

    def __repr__(self):
        return "Marker " + str(self.unique_id)


class MarkerRoadAgent(GeoAgent):
    def __init__(self, unique_id, model, shape, agent_type="marker_road"):
        super().__init__(unique_id, model, shape)
        self.atype = agent_type
        self.next_marker = tuple()
        self.second_next_marker = tuple()
        self.distance_to_safety_area = 0

    def set_distance_to_safety_area(self, distance):
        self.distance_to_safety_area = distance

    def set_next_marker(self, next_marker):
        self.next_marker = next_marker

    def get_next_marker(self):
        return self.next_marker

    def get_distance(self):
        return self.distance_to_safety_area

    def set_second_next_marker(self, second_next_marker):
        self.second_next_marker = second_next_marker

    def get_second_next_marker(self):
        return self.second_next_marker

    def __repr__(self):
        return "Marker road " + str(self.unique_id)


class MapAgent(GeoAgent):
    def __init__(self, unique_id, model, shape, agent_type="map"):
        super().__init__(unique_id, model, shape)
        self.atype = agent_type
        self.uniqueID = unique_id

        if "passadiço" in self.uniqueID:
            self.atype = "trail"
        if "parque_estac" in self.uniqueID:
            self.atype = "parking"
        if "estrada" in self.uniqueID:
            self.atype = "street"

    def __repr__(self):
        return "Map " + str(self.unique_id)


class TrailAgent(GeoAgent):
    def __init__(self, unique_id, model, shape, agent_type="trail"):
        super().__init__(unique_id, model, shape)
        self.atype = agent_type
        self.uniqueID = unique_id

    def __repr__(self):
        return "Trail " + str(self.unique_id)

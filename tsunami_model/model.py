import random
import csv

from mesa.datacollection import DataCollector
from mesa import Model
from mesa.time import BaseScheduler, RandomActivation

from mesa_geo.geoagent import GeoAgent, AgentCreator
from mesa_geo import GeoSpace
from shapely.geometry import Point

from tsunami_model.agents import PersonAgent, MarkerAgent, MapAgent, MarkerRoadAgent


class TsunamiModel(Model):
    """Tsunami model for Figueirinha beach."""

    # Geographical parameters for desired map
    MAP_COORDS = [38.484189, -8.944787]
    geojson_regions = ["geojsons/map_figueirinha.geojson", "geojsons/landmarks1.geojson", "geojsons/landmarks22.geojson", "geojsons/map_figueirinha_complete.geojson"]
    marker_beach_id = "id"
    map_id = "Nome"
    marker_road_id = "id"

    minute: int
    second: int

    def __init__(self, pop_size, pop_child_size):
        """
        Create a new TsunamiModel
        :param pop_size:        Number of person agents
        :param pop_child_size:        Number of child agents
        """
        #self.schedule = BaseScheduler(self)
        self.schedule = RandomActivation(self)
        self.grid = GeoSpace()
        self.steps = 0
        self.counts = None
        self.reset_counts()

        self.minute = 0
        self.second = 0

        # SIR model parameters
        self.pop_size = pop_size
        self.counts["susceptible"] = pop_size
        self.counts["child_susceptible"] = pop_child_size

        self.running = True
        self.datacollector = DataCollector(
            {
                "susceptible": get_susceptible_count,
                "child_susceptible": get_child_susceptible_count,
                "safe": get_safe_count,
                "off_beach": get_off_beach_count,
            }
        )

        list_agent_coords = []

        # Set up all regions of the map

        map = AgentCreator(MapAgent, {"model": self})
        map_areas = map.from_file(self.geojson_regions[0], unique_id=self.map_id)

        marker_beach = AgentCreator(MarkerAgent, {"model": self})
        marker_beach_agents = marker_beach.from_file(self.geojson_regions[1], unique_id=self.marker_beach_id)

        marker_road = AgentCreator(MarkerRoadAgent, {"model": self})
        marker_road_agents = marker_road.from_file(self.geojson_regions[2], unique_id=self.marker_road_id)

        start_area_list = []
        other_areas_list = []
        off_beach_area = []
        safe_area = []

        for area in map_areas:
            if "pessoas" in area.unique_id or "chapeus" in area.unique_id:
                start_area_list.append(area)
            elif "escadas" in area.unique_id:
                off_beach_area.append(area)
            elif "safe" in area.unique_id:
                safe_area.append(area)
            else:
                other_areas_list.append(area)

        self.grid.add_agents(off_beach_area)
        self.grid.add_agents(marker_beach_agents)
        self.grid.add_agents(start_area_list)
        self.grid.add_agents(other_areas_list)
        self.grid.add_agents(safe_area)
        self.grid.add_agents(marker_road_agents)

        # Generate PersonAgent population
        beach_population = AgentCreator(PersonAgent, {"model": self})

        self.agents_list = []
        # Generate random location, add agent to grid and scheduler
        for i in range(pop_size):
            this_neighbourhood = self.random.randint(0, len(start_area_list) - 1)  # Region where agent starts
            center_x, center_y = start_area_list[this_neighbourhood].shape.centroid.coords.xy
            this_bounds = start_area_list[this_neighbourhood].shape.bounds

            spread_x = int(this_bounds[2] - this_bounds[0])  # Heuristic for agent spread in region
            spread_y = int(this_bounds[3] - this_bounds[1])
            this_x = center_x[0] + self.random.randint(0, spread_x) - spread_x / 2
            this_y = center_y[0] + self.random.randint(0, spread_y) - spread_y / 2

            this_person = beach_population.create_agent(Point(this_x, this_y), "P" + str(i))
            self.agents_list.append(this_person)

            agent_coords = [this_x, this_y]
            list_agent_coords.append(agent_coords)

            self.grid.add_agents(this_person)
            self.schedule.add(this_person)

        beach_child_population = AgentCreator(PersonAgent, {"model": self})

        for i in range(pop_child_size):
            this_neighbourhood = self.random.randint(0, len(start_area_list) - 1)  # Region where child agent starts
            center_x, center_y = start_area_list[this_neighbourhood].shape.centroid.coords.xy
            this_bounds = start_area_list[this_neighbourhood].shape.bounds

            spread_x = int(this_bounds[2] - this_bounds[0])  # Heuristic for child agent spread in region
            spread_y = int(this_bounds[3] - this_bounds[1])
            this_x = center_x[0] + self.random.randint(0, spread_x) - spread_x / 2
            this_y = center_y[0] + self.random.randint(0, spread_y) - spread_y / 2

            this_child = beach_child_population.create_agent(Point(this_x, this_y), "C" + str(i))
            this_child.set_agent_type("child_susceptible")
            this_child.set_agent_speed("child_susceptible")

            self.agents_list.append(this_child)

            agent_coords = [this_x, this_y]
            list_agent_coords.append(agent_coords)

            self.grid.add_agents(this_child)
            self.schedule.add(this_child)


        # Add the map agents to schedule AFTER person agents,
        # to allow them to update their color by using BaseScheduler
        for agent in start_area_list:
            self.schedule.add(agent)

        self.datacollector.collect(self)

        # safe area mais próxima para cada marker
        for m_agent in marker_beach_agents:
            distance = 10000
            for x in range(len(off_beach_area)):
                distance_x = m_agent.shape.distance(off_beach_area[x].shape)
                if distance_x < distance:
                    distance = distance_x
                    m_agent.set_distance_to_off_beach_area(distance)

        # get the distance of next marker
        for m_agent in marker_beach_agents:
            scan_distance = 10
            found_marker = False
            nearest_markers = []
            while not found_marker:
                count = 0
                nearest_markers = m_agent.model.grid.get_neighbors_within_distance(m_agent, scan_distance)

                for m in nearest_markers:
                    if m.atype == "marker_beach" and m.unique_id != m_agent.unique_id:
                        found_marker = True
                scan_distance += 5
            nearest_markers = m_agent.model.grid.get_neighbors_within_distance(m_agent, scan_distance)
            closest_marker = 0
            distance = 200
            for m_marker in nearest_markers:
                if m_marker.atype == "marker_beach" and m_marker.unique_id != m_agent.unique_id:
                    if m_marker.get_distance() < distance:
                        m_agent.set_next_marker([m_marker.shape.x, m_marker.shape.y])
                        closest_marker = m_marker
                        distance = m_marker.get_distance()

        # get closest marker of an agent
        for person in self.agents_list:
            person.set_start_position(person.shape.x, person.shape.y)
            distance_closest_marker = 1000
            marker_agents = person.model.grid.get_neighbors_within_distance(person, 1500)
            for marker_agent in marker_agents:
                if marker_agent.atype == "marker_beach":
                    distance = person.shape.distance(marker_agent.shape)
                    if distance < distance_closest_marker:
                        distance_closest_marker = distance
                        person.target_marker = [marker_agent.shape.x, marker_agent.shape.y]
                        person.second_target_marker = marker_agent.get_next_marker()

            # % of agents that follow the trail
            if person.get_break_rules_percent() > 0:
                distance = 10000
                for off_beach_areas in off_beach_area:
                    markers_in_safe_area = off_beach_areas.model.grid.get_intersecting_agents(off_beach_areas)
                    for markers in markers_in_safe_area:
                        if markers.atype == "marker_beach":
                            distance_x = person.shape.distance(markers.shape)
                            if distance_x < distance:
                                distance = distance_x
                                person.target_marker = [markers.shape.x, markers.shape.y]

        # after off beach area #########################################################################

        # safe area mais próxima para cada marker
        for m_agent in marker_road_agents:
            distance = 10000
            for x in range(len(safe_area)):
                distance_y = m_agent.shape.distance(safe_area[x].shape)
                if distance_y < distance:
                    distance = distance_y
                    m_agent.set_distance_to_safety_area(distance)

        # get the distance of next marker
        for m_agent in marker_road_agents:
            nearest_markers = m_agent.model.grid.get_neighbors_within_distance(m_agent, 20)
            second_nearest_markers = []
            closest_marker = 0

            distance = 10000
            for m_marker in nearest_markers:
                if m_marker.atype == "marker_road" and m_marker.unique_id != m_agent.unique_id:
                    second_nearest_markers.append(m_marker)
                    if m_marker.get_distance() <= distance:
                        m_agent.set_next_marker([m_marker.shape.x, m_marker.shape.y])
                        closest_marker = m_marker
                        distance = m_marker.get_distance()

            # distance to second closest marker
            second_nearest_markers.remove(closest_marker)
            
            distance_second_marker = 10000
            for m_second_marker in second_nearest_markers:
                if m_second_marker.atype == "marker_road" and m_second_marker.unique_id != m_agent.unique_id:
                    if m_second_marker.get_distance() <= distance_second_marker:
                        m_agent.set_second_next_marker([m_second_marker.shape.x, m_second_marker.shape.y])
                        distance_second_marker = m_second_marker.get_distance()

    def reset_counts(self):
        self.counts = {
            "susceptible": 0,
            "child_susceptible": 0,
            "child_off_beach": 0,
            "safe": 0,
            "off_beach": 0,
        }

    def step(self):
        """Run one step of the model."""
        self.steps += 1
        self.__update_clock()
        self.reset_counts()
        self.schedule.step()
        self.grid._recreate_rtree()  # Recalculate spatial tree, because agents are moving

        self.datacollector.collect(self)

        # Run until everyone is safe
        if self.counts["susceptible"] == 0 and self.counts["off_beach"] == 0 and self.counts["child_susceptible"] == 0 and self.counts["child_off_beach"] == 0:
            self.running = False
            # create csv file with final data
            mydict = [{'susceptible': self.counts["susceptible"],
                       'off_beach': self.counts["off_beach"],
                       'child_susceptible': self.counts["child_susceptible"],
                       'child_off_beach': self.counts["child_off_beach"],
                       'safe': self.counts["safe"],
                       'Time': str(self.minute) + ":" + str(self.second)}]

            fields = ['susceptible', 'off_beach', 'child_susceptible', 'child_off_beach', 'safe', 'Time']

            filename = "experience_beach_records.csv"

            with open(filename, 'w') as csvfile:
                # creating a csv dict writer object
                writer = csv.DictWriter(csvfile, fieldnames=fields)

                # writing headers (field names)
                writer.writeheader()

                # writing data rows
                writer.writerows(mydict)

    def __update_clock(self) -> None:
        self.second += 1
        if self.second == 60:
            self.minute += 1
            self.second = 0
        # Run until 35 minutes
        if self.minute == 35:
            self.running = False

            # create csv file with final data
            mydict = [{'susceptible': self.counts["susceptible"],
                       'off_beach': self.counts["off_beach"],
                       'child_susceptible': self.counts["child_susceptible"],
                       'child_off_beach': self.counts["child_off_beach"],
                       'safe': self.counts["safe"],
                       'Time': str(self.minute) + ":" + str(self.second)}]

            fields = ['susceptible', 'off_beach', 'child_susceptible', 'child_off_beach', 'safe', 'Time']

            filename = "experience_beach_records.csv"

            with open(filename, 'w') as csvfile:
                # creating a csv dict writer object
                writer = csv.DictWriter(csvfile, fieldnames=fields)

                # writing headers (field names)
                writer.writeheader()

                # writing data rows
                writer.writerows(mydict)


# Functions needed for datacollector
def get_susceptible_count(model):
    return model.counts["susceptible"]


def get_child_susceptible_count(model):
    return model.counts["child_susceptible"]


def get_child_off_beach_count(model):
    return model.counts["child_off_beach"]


def get_off_beach_count(model):
    return model.counts["off_beach"]


def get_safe_count(model):
    return model.counts["safe"]




import math
import sys
from dataclasses import dataclass, field
from typing import List, Dict

inputFilename = sys.argv[1]
outputFilename = sys.argv[2]

@dataclass
class City:
    name: str
    must_host: bool
    x: int
    y: int
    time_to_prepare: int
    availability: List[bool]
    population: List[int]
    
    def __str__(self):
        host_status = "Required" if self.must_host else "Optional"
        return (f"City: {self.name} ({self.x}, {self.y})\n"
                f"  - Host Status: {host_status}\n"
                f"  - Prep Time: {self.time_to_prepare} days\n"
                f"  - Avg Population: {sum(self.population) // len(self.population) if self.population else 0}")

@dataclass
class Team:
    name: str
    x: int
    y: int
    max_distance: int
    
    def __str__(self):
        return (f"Team: {self.name}\n"
                f"  - Position: ({self.x}, {self.y})\n"
                f"  - Max Travel Distance: {self.max_distance}")

@dataclass
class Instance:
    alpha: float
    beta: float
    gamma: float
    phi: float
    cities_for_event: int
    cities_available: int
    teams_available: int
    cities: List[City]
    teams: List[Team]
    distances: Dict[str, Dict[str, float]]
    
    def __str__(self):
        return (f"--- Problem Instance ---\n"
                f"Weights: α={self.alpha}, β={self.beta}, γ={self.gamma}, φ={self.phi}\n"
                f"Event Scale:\n"
                f"  - Required Cities for Event: {self.cities_for_event}\n"
                f"  - Available Cities Pool: {self.cities_available}\n"
                f"  - Total Teams Participating: {self.teams_available}\n"
                f"Data Loaded:\n"
                f"  - Cities List: {len(self.cities)} objects\n"
                f"  - Teams List: {len(self.teams)} objects\n"
                f"  - Distance Matrix: {len(self.distances)}x{len(self.distances)}")

def read_instance(path: str):
    f = open(path, 'r', encoding='utf-8')
    
    line1 = f.readline().split()
    alpha, beta, gamma, phi = map(float, line1)

    line2 = f.readline().split()
    cities_for_event, cities_available, teams_available = map(int, line2)

    cities = []
    for i in range(cities_available):
        name = f.readline().strip()
        
        must_host = f.readline().strip().startswith('T')
        
        x, y, time_to_prepare = map(int, f.readline().split())
        
        availability_strs = f.readline().split()
        availability = [s.startswith('T') for s in availability_strs]
        
        line = f.readline().split()
        pop_values = list(map(int, line))
        
        cities.append(City(name, must_host, x, y, time_to_prepare, availability, pop_values))

    teams = []
    for i in range(teams_available):
        team_name = f.readline().strip()
        tx, ty, t_max_dist = map(int, f.readline().split())
        teams.append(Team(team_name, tx, ty, t_max_dist))

    countI = 0
    distances = {}
    for c1 in cities:
        countI += 1
        distances[c1.name] = {}
        for c2 in cities:
            dist = round(math.sqrt((c2.x - c1.x)**2 + (c2.y - c1.y)**2))
            distances[c1.name][c2.name] = dist

    return Instance(alpha, beta, gamma, phi, cities_for_event, 
                    cities_available, teams_available, cities, teams, distances)

def read_cities(number_of_events: int, path: str):
    f = open(path, 'r', encoding='utf-8')
    return [f.readline().strip() for _ in range(number_of_events)]

def evaluate(instance, route):

    selected_cities = []
    for name in city_list_strings:
        for c in inst.cities:
            if c.name == name:
                selected_cities.append(c)
                break
                
    for c in inst.cities:
        if c.must_host:
            hosted = False
            for name in city_list_strings:
                if c.name == name:
                    hosted = True
            if not hosted:
                print("INFAC dut to not hosting at", c.name)
                
    distance_reuniao = 0
    number_of_participantes = 0
    first_city = selected_cities[0]

    for team in inst.teams:
        dist = round(math.sqrt((first_city.x - team.x)**2 + (first_city.y - team.y)**2))
        if dist <= team.max_distance:
            distance_reuniao += dist
            number_of_participantes += 1

    distance_evento = 0
    total_population = selected_cities[0].population[0] 

    for i in range(1, inst.cities_for_event):
        curr_city = selected_cities[i]
        prev_city = selected_cities[i-1]
        
        distance_evento += inst.distances[curr_city.name][prev_city.name]
        total_population += curr_city.population[i]

        for j in range(curr_city.time_to_prepare + 1):
            if i - j >= 0:
                if not curr_city.availability[i - j]:
                    print("INFAC due to wheather at", curr_city.name)
                    
    distance_evento += inst.distances[first_city.name][selected_cities[-1].name]

    return inst.alpha * distance_reuniao + inst.beta * distance_evento - inst.gamma * total_population - inst.phi * number_of_participantes
    

inst = read_instance(inputFilename)

city_list_strings = read_cities(inst.cities_for_event, outputFilename)

obj_value = evaluate(inst, city_list_strings)

print(obj_value)
"""Environment of the case study: routes, map, simulation plans/options/regions.

Java: TRoute, TEnvironment, TPosition_Coords, TPlan_Simulation (extends TPlan), TOption_Simulation
(extends TOption), TRegion_Simulation, TRegion_Simulation2.

Java behaviour kept on purpose:
* ``Add_Arch`` creates the outward route (even number) and the reverse one (odd), numbering from 0;
  both use the first motor of the colour (``Motors.get(0)``).
* ``Dfs`` only follows arcs whose status is ``"Green"`` or ``"Under_maintenance"``; after each
  recursion the route number is removed *by value* from the current path.
* ``Find_All_Paths_From_A_Damaged_Route`` starts from the *departure of the damaged route* and
  only follows that route (then ``Dfs``).
* ``Compute_Sum_Weights_Routes`` divides by the number of routes: 0/0 is ``NaN`` as in Java.
* ``Get_Route(index)`` returns ``None`` only for ``index >= size``; negative indexes raise.
* ``TRoute.Set_Busy`` writes ``Interrupted`` (sic).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Set

from catalina.handlers import TripleObject
from catalina.model import Region
from catalina.plan import Option

from .domain import (MyCollections, TCity, TColor, TMotor, TPanorama, TSpeed, TTypeQualityDesire)


class PositionCoords:
    """Java: TPosition_Coords."""

    def __init__(self, city: int, route: int, step: int):
        self.city = city
        self.route = route
        self.step = step

    def get_route(self) -> int:
        return self.route

    def set_route(self, route: int) -> None:
        self.route = route

    def get_step(self) -> int:
        return self.step

    def set_step(self, step: int) -> None:
        self.step = step

    def get_city(self) -> int:
        return self.city

    def set_city(self, city: int) -> None:
        self.city = city


class Route:
    """Java: TRoute."""

    def __init__(self, departure: TCity, destination: TCity, color: TColor, steps_number: int,
                 locomotive: TMotor, panorama: TPanorama, speed: TSpeed, route_number: int):
        self.departure = departure
        self.destination = destination
        self.color = color
        self.steps_number = steps_number
        self.step_interrupted = 0
        self.interrupted = False
        self.busy = False
        self.fredned = False
        self.locomotive = locomotive
        self.the_panorama = panorama
        self.speed = speed
        self.route_number = route_number
        self.route_used_by_agent = 0
        self.duration_closed = 0
        self.route_status = "Green"
        self.route_locomotive = self.locomotive.get_value() * self.steps_number
        self.route_panorama = self.the_panorama.get_value()
        self.route_speed = self.speed.get_value()
        self.path_time = float(self.steps_number + 1) / self.route_speed
        self.total_rounds = int(math.ceil(self.path_time))

    # ---- getters (Java names)
    def get_path_time(self) -> float:
        return self.path_time

    def get_numered_route(self) -> int:
        return self.route_number

    def get_departure(self) -> TCity:
        return self.departure

    def get_destination(self) -> TCity:
        return self.destination

    def get_color(self) -> TColor:
        return self.color

    def get_steps_number(self) -> int:
        return self.steps_number

    def get_interrupted(self) -> bool:
        return self.interrupted

    def set_interrupted(self, value: bool) -> None:
        self.interrupted = value

    def get_busy(self) -> bool:
        return self.busy

    def set_busy(self, value: bool) -> None:
        self.interrupted = value          # Java bug kept: writes Interrupted

    def get_steps_interrupted(self) -> int:
        return self.step_interrupted

    def set_pieces_interrupted(self, value: int) -> None:
        self.step_interrupted = value

    def get_locomotive(self) -> TMotor:
        return self.locomotive

    def get_speed(self) -> TSpeed:
        return self.speed

    def get_route_locomotive(self) -> float:
        return self.route_locomotive

    def get_route_panorama(self) -> float:
        return self.route_panorama

    def get_route_speed(self) -> int:
        return self.route_speed

    def get_total_rounds(self) -> int:
        return self.total_rounds

    def set_duration_closed(self, value: int) -> None:
        self.duration_closed = value

    def get_duration_closed(self) -> int:
        return self.duration_closed

    def get_path_time_starting_by_step(self, starting_step: int) -> float:
        return float(self.steps_number + 1 - starting_step) / self.route_speed

    def get_total_rounds_starting_by_step(self, starting_step: int) -> int:
        return int(math.ceil(self.get_path_time_starting_by_step(starting_step)))

    def get_route_status(self) -> str:
        return self.route_status

    def set_route_status(self, value: str) -> None:
        self.route_status = value

    def __repr__(self) -> str:
        return f"Route({self.route_number}: {self.departure}->{self.destination} {self.color} x{self.steps_number})"


class PlanSimulation:
    """Java: TPlan_Simulation (extends TPlan, whose only content is a name)."""

    def __init__(self) -> None:
        self.name = ""
        self.destinations: List[TCity] = []
        self.total_weights: Dict[TTypeQualityDesire, float] = {}
        self.routes: List[int] = []
        self.path_time: float = 0.0
        self.next_position = TripleObject()

    def insert_path_by_routes(self, destinations: List[TCity], numbered_route: List[int],
                              weights: Dict[TTypeQualityDesire, float], path_time: float) -> None:
        self.destinations.extend(destinations)
        self.routes.extend(numbered_route)
        self.total_weights.update(weights)
        self.path_time = path_time

    def insert_path_by_stations(self, routes: List[Route], numbered_destinations: List[int],
                                weights: Dict[TTypeQualityDesire, float], path_time: float) -> None:
        """Fill the plan from a list of routes and the numbered destinations: the stations visited, the route
        numbers, the summed quality weights and the path time.
        """
        destinations: List[TCity] = []
        if len(numbered_destinations) > 0:
            destinations.append(routes[0].get_departure())
            for i in range(len(numbered_destinations)):
                destinations.append(routes[i].get_destination())
        self.routes.extend(numbered_destinations)
        self.destinations.extend(destinations)
        self.total_weights.update(weights)
        self.path_time = path_time

    def copy_plan(self, plan_path: "PlanSimulation") -> None:
        self.routes.extend(plan_path.routes)
        self.destinations.extend(plan_path.destinations)
        self.total_weights.update(plan_path.total_weights)
        self.path_time = plan_path.path_time

    def get_next_position(self) -> TripleObject:
        return self.next_position

    def set_next_position(self, next_position: TripleObject) -> None:
        self.next_position.set_object_first(next_position.get_object_first())
        self.next_position.set_object_second(next_position.get_object_second())
        self.next_position.set_object_third(next_position.get_object_third())

    def get_routes(self) -> List[int]:
        return self.routes


class OptionSimulation(Option):
    """Java: TOption_Simulation (extends TOption)."""

    def __init__(self, plans, precondition, cost: Optional[float],
                 quality_list: Optional[Dict[TTypeQualityDesire, float]]):
        super().__init__()
        if plans is not None:
            self.get_plan_actions().extend(plans)
        self.precondition = precondition
        self.cost = cost
        self.quality_list = quality_list
        self.path = PlanSimulation()

    def clear(self) -> None:
        super().clear()
        self.precondition.clear()      # NPE in Java when precondition is null: kept
        self.quality_list.clear()

    def set_plan_actions(self, plan_actions) -> None:
        self.clear()
        self.get_plan_actions().extend(plan_actions)

    def get_precondition(self):
        return self.precondition

    def set_precondition(self, precondition) -> None:
        self.precondition = precondition

    def get_cost(self):
        return self.cost

    def set_cost(self, cost) -> None:
        self.cost = cost

    def get_quality_list(self) -> Optional[Dict[TTypeQualityDesire, float]]:
        return self.quality_list

    def set_quality_list(self, quality_list) -> None:
        self.quality_list = quality_list

    def get_action_to_do_id(self) -> int:
        return self.get_id_current_action()

    def inc_action_to_do_id(self) -> None:
        self.next_id_current_action()


class RegionSimulation(Region):
    """Java: TRegion_Simulation (one region per route, named ``Route_<n>``)."""

    def __init__(self, route: Route):
        super().__init__()
        self.route = route
        self.set_name("Route_" + str(route.get_numered_route()))

    def get_route(self) -> Route:
        return self.route


class RegionSimulation2(Region):
    """Java: TRegion_Simulation2."""

    def __init__(self) -> None:
        super().__init__()
        self.destinations: List[TCity] = []
        self.routes: List[Route] = []
        self.integer_routes: List[int] = []

    def is_empty(self) -> bool:
        return not self.destinations and not self.routes and not self.integer_routes

    def clear(self) -> None:
        self.destinations.clear()
        self.routes.clear()
        self.integer_routes.clear()


class Environment:
    """Java: TEnvironment."""

    def __init__(self) -> None:
        self.routes_number = -1       # even route number = inserted route, odd = its reverse
        self.my_collection = MyCollections()
        self.neighbors: Dict[TCity, List[Route]] = {}
        self.all_routes: List[Route] = []

    def clone(self) -> "Environment":
        cloned = Environment()
        cloned.routes_number = self.routes_number
        cloned.all_routes.extend(self.all_routes)
        cloned.neighbors.update(self.neighbors)
        return cloned

    def add_arch(self, departure: TCity, destination: TCity, assigned_color: TColor, steps: int) -> None:
        """Add a bidirectional arc: two routes (outward gets an even number, the reverse the next odd one) with
        the colour's panorama/speed and its first motor.
        """
        color_route = self.my_collection.color_ruotes[assigned_color]
        self.routes_number += 1
        outward = Route(departure, destination, assigned_color, steps, color_route.motors[0],
                        color_route.panorama, color_route.speed, self.routes_number)
        self.routes_number += 1
        reverse = Route(destination, departure, assigned_color, steps, color_route.motors[0],
                        color_route.panorama, color_route.speed, self.routes_number)
        self.neighbors.setdefault(departure, []).append(outward)
        self.neighbors.setdefault(destination, []).append(reverse)
        self.all_routes.append(outward)
        self.all_routes.append(reverse)

    # ---- path search
    def find_all_paths(self, departure: TCity, destination: TCity) -> List[PlanSimulation]:
        visited: Set[TCity] = set()
        current_path: List[TCity] = []
        all_paths: List[List[TCity]] = []
        current_routes: List[int] = []
        all_routes: List[List[int]] = []
        self.dfs(departure, destination, visited, current_path, all_paths, current_routes, all_routes, -1)
        return self._plans(all_paths, all_routes)

    def find_all_paths_from_a_damaged_route(self, route_number_departure: int, step_departure: int,
                                            destination_city: TCity) -> List[PlanSimulation]:
        """All simple paths to ``destination_city`` that start by continuing on a route (the car is already on
        it); used after a danger on the route.
        """
        visited: Set[TCity] = set()
        current_path: List[TCity] = []
        all_paths: List[List[TCity]] = []
        current_routes: List[int] = []
        all_routes: List[List[int]] = []
        route_departure = self.get_route(route_number_departure)
        self.dfs_from_a_damaged_route(route_departure, destination_city, visited, current_path, all_paths,
                                      current_routes, all_routes, -1)
        return self._plans(all_paths, all_routes)

    def _plans(self, all_paths, all_routes) -> List[PlanSimulation]:
        """Wrap the DFS results into ``PlanSimulation`` objects (path, routes, summed weights, path time)."""
        plans: List[PlanSimulation] = []
        for i in range(len(all_routes)):
            plan = PlanSimulation()
            plan.insert_path_by_routes(all_paths[i], all_routes[i],
                                       self.compute_sum_weights_routes(all_routes[i]),
                                       self.compute_path_time_routes(all_routes[i]))
            plans.append(plan)
        return plans

    def compute_sum_weights_routes(self, routes_path: List[int]) -> Dict[TTypeQualityDesire, float]:
        """Average motor, panorama and speed values over the routes of a path (NaN for an empty path, as Java's
        0.0/0).
        """
        motor = panorama = speed = 0.0
        n = len(routes_path)
        for index in routes_path:
            route = self.all_routes[index]
            motor += route.get_route_locomotive()
            panorama += route.get_route_panorama()
            speed += route.get_route_speed()
        if n == 0:
            avg = (math.nan, math.nan, math.nan)         # Java: 0.0 / 0 == NaN
        else:
            avg = (motor / n, panorama / n, speed / n)
        return {TTypeQualityDesire.Motor: avg[0], TTypeQualityDesire.Panorama: avg[1],
                TTypeQualityDesire.Speed: avg[2]}

    def compute_path_time_routes(self, routes_path: List[int]) -> float:
        path_time = 0.0
        under_maintenance = 0
        for index in routes_path:
            route = self.all_routes[index]
            path_time += route.get_path_time()
            under_maintenance += route.get_duration_closed()
        return path_time + under_maintenance

    def dfs(self, current_node: TCity, destination: TCity, visited: Set[TCity], current_path: List[TCity],
            all_paths: List[List[TCity]], current_path_integers: List[int],
            all_paths_integers: List[List[int]], arch_index: int) -> None:
        """Depth-first search of every simple path from ``current_node`` to ``destination``, following only
        arcs whose status is Green or Under_maintenance.
        """
        visited.add(current_node)
        current_path.append(current_node)
        if arch_index > -1:
            current_path_integers.append(arch_index)
        if current_node is destination:
            all_paths.append(list(current_path))
            all_paths_integers.append(list(current_path_integers))
        else:
            for arc in self.neighbors.get(current_node, ()):
                if arc.get_destination() not in visited:
                    if arc.get_route_status() in ("Green", "Under_maintenance"):
                        arch_index = arc.route_number
                        self.dfs(arc.get_destination(), destination, visited, current_path, all_paths,
                                 current_path_integers, all_paths_integers, arch_index)
                        if arch_index > -1:
                            try:
                                current_path_integers.remove(arch_index)    # by value, like List.remove(Object)
                            except ValueError:
                                pass
        current_path.pop()
        visited.discard(current_node)

    def dfs_from_a_damaged_route(self, arc: Route, destination: TCity, visited: Set[TCity],
                                 current_path: List[TCity], all_paths: List[List[TCity]],
                                 current_path_integers: List[int],
                                 all_paths_integers: List[List[int]], arch_index: int) -> None:
        """Same search, but the first arc to follow is given (the route where the car stands)."""
        current_node = arc.get_departure()
        visited.add(current_node)
        current_path.append(current_node)
        if arch_index > -1:
            current_path_integers.append(arch_index)
        if arc.get_destination() not in visited:
            if arc.get_route_status() in ("Green", "Under_maintenance"):
                arch_index = arc.route_number
                self.dfs(arc.get_destination(), destination, visited, current_path, all_paths,
                         current_path_integers, all_paths_integers, arch_index)
                if arch_index > -1:
                    try:
                        current_path_integers.remove(arch_index)
                    except ValueError:
                        pass
        current_path.pop()
        visited.discard(current_node)

    # ---- queries
    def get_routes(self, departure: TCity, destination: TCity) -> List[Route]:
        routes: List[Route] = []
        if departure is not destination:
            for route in self.neighbors.get(departure, ()):
                if route.get_destination() is destination:
                    routes.append(route)
        return routes

    def get_route(self, index: int) -> Optional[Route]:
        if index < len(self.all_routes):
            if index < 0:
                raise IndexError(f"Index {index} out of bounds for length {len(self.all_routes)}")
            return self.all_routes[index]
        return None

    def route_at(self, index: int) -> Route:
        """Java ``All_Routes.get(index)``: negative or too large indexes raise (Python would wrap)."""
        if index < 0 or index >= len(self.all_routes):
            raise IndexError(f"Index {index} out of bounds for length {len(self.all_routes)}")
        return self.all_routes[index]

    def get_neighbor_stations(self, station: TCity) -> List[TCity]:
        return [r.get_destination() for r in self.neighbors.get(station, ())]

    def get_routes_nearby_cities(self, station: TCity) -> List[Route]:
        return list(self.neighbors.get(station, ()))

    def get_routes_number(self) -> int:
        return self.routes_number

    def get_specular_route(self, a_route: int) -> int:
        if a_route < 0:
            return a_route
        return a_route + 1 if a_route % 2 == 0 else a_route - 1

    def get_specular_step_in_route(self, a_route: int, a_step: int) -> int:
        specular_route = self.get_specular_route(a_route)
        if specular_route == -1:
            return 0
        route = self.all_routes[specular_route]
        return route.get_steps_number() - a_step + 1


def create_map(env: Environment) -> Environment:
    """Java: ``Autonomous_Vehicle_Demo.Create_Map`` (data generated from the Java source)."""
    from .map_data import ARCHES
    for departure, destination, color, steps in ARCHES:
        env.add_arch(TCity[departure], TCity[destination], TColor[color], steps)
    return env

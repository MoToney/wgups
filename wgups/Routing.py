from datetime import datetime, timedelta

from wgups.Package import Package
from wgups.datastore.DistanceMap import DistanceMap
from wgups.datastore.PackageHashMap import PackageHashMap, SlotStatus
from wgups.dataloader.PackageLoader import PackageLoader


class Routing:

    def __init__(self, distance_map: DistanceMap):
        self.distance_map = distance_map
        self.group_to_route: dict[frozenset[int], int] = {}

    def build_route(self, route_id:int, start:str, packages:PackageHashMap,visited_ids:set, current_time:datetime,
                    max_capacity:int, total_dist:int = 0):
        route = [("None",start)]
        current_location = start


        # get all possible choices for this route
        available_packages = self.get_available_packages(packages=packages, visited_ids=visited_ids,
                                                         current_time=current_time, route_id=route_id)

        while len(route) < max_capacity:
            scored_packages = self.get_scored_packages(available_packages=available_packages, current_time=current_time,
                                                       current_location=current_location, visited_ids=visited_ids,
                                                       route_id=route_id)

            # if no more valid options
            if not scored_packages:
                break

            # select lowest cost package
            best_package = self.select_best_package(scored_packages=scored_packages)

            # add group if needed
            group = self.get_package_group(best_package=best_package, packages=packages, visited_ids=visited_ids)

            # check if adding group exceeds capacity
            if len(route) + len(group) > max_capacity:
                print("mark_group_as_skipped(group)")
                continue

            # add package(s) to route
            current_location, current_time, total_dist = self.add_group_to_route(group=group, route=route,
                                                                                 visited_ids=visited_ids,
                                                                     current_location=current_location,
                                                                     current_time=current_time, total_dist=total_dist)

            #refresh possible choices for next stop
            available_packages = self.get_available_packages(packages, visited_ids, current_time, route_id)

        return route, self.group_to_route, visited_ids, current_time, total_dist, available_packages

    def get_available_packages(self, packages:PackageHashMap, visited_ids:set, current_time:datetime,
                               route_id:int) -> list[Package]:
        available_packages = []
        for package in packages.packages_table:
            if not isinstance(package, Package):
                continue
            if package.package_id not in visited_ids:
                if package.available_time is None or package.available_time <= current_time.time():
                    if package.required_truck is None or package.required_truck == route_id:
                        available_packages.append(package)
        return available_packages

    def score(self, package: Package, current_time:datetime, current_location:str, visited_ids:set,
              route_id:int) -> float:
        distance = self.distance_map.get_distance(current_location, package.address_w_zip)

        if package.deadline:
            time_remaining = (package.deadline - current_time).total_seconds() / 60
        else:
            time_remaining = None

        urgency = 0 if time_remaining is None else 1 /max(time_remaining, 1)

        penalty = 0
        if self.violates_group_constraint(package, visited_ids, route_id):
            penalty += 10000
        if package.required_truck is not None and package.required_truck != route_id:
            penalty += 10000

        ALPHA = 1.0
        BETA = 5.0

        return distance * ALPHA + urgency * BETA + penalty

    def get_scored_packages(self, available_packages:list[Package], current_time:datetime, current_location:str,
                            visited_ids:set, route_id:int) -> list[tuple[Package, float]]:
        scored = []
        for package in available_packages:
            if self.violates_group_constraint(package, visited_ids, route_id):
                continue
            cost = self.score(package, current_time, current_location, visited_ids, route_id)
            scored.append((package, cost))
        return scored

    def select_best_package(self, scored_packages:list[tuple[Package, float]]) -> Package:
        lowest_cost = float("inf")
        for package, cost in scored_packages:
            if cost < lowest_cost:
                lowest_cost = cost
                best_package = package
        return best_package

    def violates_group_constraint(self, package: Package, visited_ids:set, route_id:int ) -> bool:
        group = package.must_be_delivered_with

        if group is None or len(group) == 0:
            return False

        full_group_ids = set(group + [package.package_id])

        frozen_group = frozenset(full_group_ids)

        visited_in_group = visited_ids & full_group_ids

        #case 1: Partial group already visited (split delivery)
        if 0 < len(visited_in_group) < len(full_group_ids):
            return True

        if frozen_group in self.group_to_route and self.group_to_route[frozen_group] != route_id:
            return True

        return False

    def get_package_group(self, best_package:Package, packages:PackageHashMap, visited_ids:set) -> list[Package]:
        group = [best_package]
        if best_package.must_be_delivered_with:
            for gid in best_package.must_be_delivered_with:
                p = packages.search_package(gid)
                if p and p.package_id not in visited_ids:
                    group.append(p)
        return group

    def add_group_to_route(self, group:list[Package], route:list[tuple[str,str]], visited_ids:set, current_location:str,
                           current_time:datetime, total_dist: float):
        for pkg in group:
            dist = self.distance_map.get_distance(current_location, pkg.address_w_zip)
            travel_time = self.compute_travel_time(dist)
            current_time += travel_time
            total_dist += dist
            visited_ids.add(pkg.package_id)
            route.append((str(pkg.package_id),pkg.address_w_zip))
            current_location = pkg.address_w_zip
        return current_location, current_time, total_dist

    def compute_travel_time(self, distance:float) -> timedelta:
        hours = distance / 18.0
        seconds = hours * 3600
        return timedelta(seconds=seconds)

    def old_cost(self, package: Package, current_time:datetime, current_location:str) -> float:
        distance = self.distance_map.get_distance(current_location, package.address_w_zip)

        if package.deadline:
            time_remaining = (package.deadline - current_time).total_seconds() / 60
            if time_remaining <= 0:
                return float('inf')
            return distance * (60 / time_remaining) # more urgent
        return distance * 2 # no deadline = deprioritized

"""route = routing.build_route(2, "HUB", packages, set() ,
                            datetime(1900,1,1,8,0), 16)"""






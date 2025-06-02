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
                    max_capacity:int) -> list[Package]:
        route = [start]
        current_location = start

        # get all possible choices for this route
        available_pckgs = self.get_available_packages(packages, visited_ids, current_time, route_id)

        while len(visited_ids) < max_capacity:
            '''scored_pckgs = []

            # calculate cost for each candidate
            for p in available_pckgs:
                if self.violates_group_constraint(p, visited_ids, route_id):
                    print(f"{p} violation")
                    continue

                cost = self.cost_v2(p,current_time, current_location, visited_ids, route_id)
                cost2 = self.cost(p,current_time, current_location)
                print(f"{p.package_id, p.address_w_zip, p.deadline, p.must_be_delivered_with}"
                      f"truck:{p.required_truck} cost: {cost} oldcost: {cost2}")
                scored_pckgs.append((p,cost))
            '''
            scored_pckgs = self.get_scored_candidates(available_pckgs, current_time, current_location,visited_ids, route_id)

            # if no more valid options
            if not scored_pckgs:
                break

            # select lowest cost package
            """best_cost = float("inf")
            for package,cost in scored_pckgs:
                if cost < best_cost:
                    best_cost = cost
                    best_package = package"""
            best_package = self.select_lowest_cost(scored_pckgs)

            # add group if needed
            """group = [best_package]
            if best_package.must_be_delivered_with:
                for gid in best_package.must_be_delivered_with:
                    gpackage = packages.search_package(gid)
                    if gpackage.package_id not in visited_ids:
                        group.append(gpackage)"""
            group = self.get_package_group(best_package, packages, visited_ids)

            # check if adding group exceeds capacity
            if len(visited_ids) + len(group) > max_capacity:
                print("mark_group_as_skipped(group)")
                continue

            # add package(s) to route
            current_location, current_time = self.add_group_to_route(group, route, visited_ids, current_location, current_time)

            #refresh possible choices for next stop
            available_pckgs = self.get_available_packages(packages, visited_ids, current_time, route_id)

        return route

    """            group = self.get_full_group(next_package, packages)
            unvisited_group = []
            for pack in group:
                if pack.package_id not in visited_ids:
                    unvisited_group.append(pack)

            #check if group fits
            if len(visited_ids) + len(unvisited_group) > max_capacity:
                continue

            # lock group to route before adding
            group_key = frozenset(pack.package_id for pack in group)
            if group_key not in self.group_to_route:
                self.group_to_route[group_key] = route_id

            #add each package in the group
            for pkg in unvisited_group:
                route.append(pkg.address_w_zip)
                visited_ids.add(pkg.package_id)
                current_location = pkg.address_w_zip

            '''if next_package.must_be_delivered_with:
                if len(next_package.must_be_delivered_with)
                for pid in next_package.must_be_delivered_with:
                    package = packages.search_package(pid)
                    if pid not in visited_ids:
                        print(package)
                        route.append(package)
                        visited_ids.add(package.package_id)'''"""



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

    def cost_v2(self, package: Package, current_time:datetime, current_location:str, visited_ids:set,
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

    def cost(self, package: Package, current_time:datetime, current_location:str) -> float:
        distance = self.distance_map.get_distance(current_location, package.address_w_zip)

        if package.deadline:
            time_remaining = (package.deadline - current_time).total_seconds() / 60
            if time_remaining <= 0:
                return float('inf')
            return distance * (60 / time_remaining) # more urgent
        return distance * 2 # no deadline = deprioritized

    def select_best_package(self, avail_packages: list[Package], current_time:datetime,
                            current_location:str) -> Package:
        cost = float('inf')
        best_package = None
        for pckg in avail_packages:
            potential_cost = self.cost(pckg, current_time, current_location)
            if best_package is None or potential_cost < cost:
                best_package = pckg
                cost = potential_cost
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

        '''if len(visited_ids) + len(full_group_ids - visited_ids) > truck_capacity:
            return True  # Group too large to fit now'''

    def get_full_group(self, package:Package, packages:PackageHashMap) -> list[Package]:
        group_ids = set(package.must_be_delivered_with or [])
        group_ids.add(package.package_id)

        group = []
        for pid in group_ids:
            pkg = packages.search_package(pid)
            if pkg:
                group.append(pkg)
        return group

    def compute_travel_time(self, distance:float) -> timedelta:
        hours = distance / 18.0
        seconds = hours * 3600
        return timedelta(seconds=seconds)

    def get_scored_candidates(self, available_packages:list[Package], current_time:datetime, current_location:str,
                              visited_ids:set, route_id:int) -> list[Package]:
        scored = []
        for package in available_packages:
            if self.violates_group_constraint(package, visited_ids, route_id):
                continue
            cost = self.cost_v2(package, current_time, current_location, visited_ids, route_id)
            scored.append((package, cost))
        return scored

    def select_lowest_cost(self, scored_packages:list[tuple[Package, float]]) -> Package:
        lowest_cost = float("inf")
        for package, cost in scored_packages:
            if cost < lowest_cost:
                lowest_cost = cost
                best_package = package
        return best_package

    def get_package_group(self, best_package:Package, packages:PackageHashMap, visited_ids:set) -> list[Package]:
        group = [best_package]
        if best_package.must_be_delivered_with:
            for gid in best_package.must_be_delivered_with:
                p = packages.search_package(gid)
                if p and p.package_id not in visited_ids:
                    group.append(p)
        return group

    def add_group_to_route(self, group:list[Package], route:list[str], visited_ids:set, current_location:str,
                           current_time:datetime):
        for pkg in group:
            dist = self.distance_map.get_distance(current_location, pkg.address_w_zip)
            travel_time = self.compute_travel_time(dist)
            current_time += travel_time
            visited_ids.add(pkg.package_id)
            route.append(pkg.address_w_zip)
            current_location = pkg.address_w_zip
        return current_location, current_time


packages = PackageLoader.load_from_file("../data/packages.csv",
                                        PackageHashMap(61, 1, 1, .75))
distances = DistanceMap("../data/distances.csv")
routing = Routing(distances)
availables = routing.get_available_packages(packages, set(),
                                            datetime(1900, 1, 1, 8, 0), 2)




route = routing.build_route(2, "HUB", packages, set() ,
                            datetime(1900,1,1,8,0), 16)
print(route)








"""
to get the time it'll take do distance/mph and then find a way to implement this into the NN algorithm
"""



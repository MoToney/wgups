from datetime import datetime

from wgups.Package import Package
from wgups.datastore.DistanceMap import DistanceMap
from wgups.datastore.PackageHashMap import PackageHashMap, SlotStatus
from wgups.dataloader.PackageLoader import PackageLoader


class Routing:

    def __init__(self, distance_map: DistanceMap):
        self.distance_map = distance_map

    def build_route(self, start:str, packages:PackageHashMap,visited_ids:set, current_time:datetime, max_capacity:int) -> list[Package]:
        route = [start]
        current_location = start

        while len(visited_ids) < max_capacity:
            available = self.get_available_packages(packages, visited_ids, current_time)
            next_package = self.select_best_package(available, current_time, current_location)

            if next_package is None:
                break

            route.append(next_package.address_w_zip)
            visited_ids.add(next_package.package_id)
            current_location = next_package.address_w_zip

            '''if next_package.must_be_delivered_with:
                if len(next_package.must_be_delivered_with)
                for pid in next_package.must_be_delivered_with:
                    package = packages.search_package(pid)
                    if pid not in visited_ids:
                        print(package)
                        route.append(package)
                        visited_ids.add(package.package_id)'''
        return route


    def get_available_packages(self, packages:PackageHashMap, visited_ids:set, current_time:datetime) -> list[Package]:
        available_packages = []
        for package in packages.packages_table:
            if not isinstance(package, Package):
                continue
            if package.package_id not in visited_ids and isinstance(package, Package):
                if package.available_time is None or package.available_time <= current_time.time():
                    available_packages.append(package)
        return available_packages


    def cost(self, package: Package, current_time:datetime, current_location:str) -> float:
        distance = self.distance_map.get_distance(current_location, package.address_w_zip)

        if package.deadline:
            time_remaining = (package.deadline - current_time).total_seconds() / 60
            if time_remaining <= 0:
                return float('inf')
            return distance * (60 / time_remaining) # more urgent
        return distance * 2 # no deadline = deprioritized

    def select_best_package(self, avail_packages, current_time:datetime, current_location:str) -> Package:
        cost = float('inf')
        best_package = None
        for pckg in avail_packages:
            potential_cost = self.cost(pckg, current_time, current_location)
            if best_package is None or potential_cost < cost:
                best_package = pckg
                cost = potential_cost
        return best_package







packages = PackageLoader.load_from_file("../data/packages.csv", PackageHashMap(61, 1, 1, .75))
distances = DistanceMap("../data/distances.csv")
routing = Routing(distances)

availables = routing.get_available_packages(packages,set(), datetime(1900, 1, 1,8,0))

route = routing.build_route("HUB", packages,set() , datetime(1900,1,1,8,0), 10)
print(route)







"""
to get the time it'll take do distance/mph and then find a way to implement this into the NN algorithm
"""



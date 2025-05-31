from wgups.Package import Package
from wgups.datastore.DistanceMap import DistanceMap
from wgups.datastore.PackageHashMap import PackageHashMap, SlotStatus
from wgups.dataloader.PackageLoader import PackageLoader


class Routing:

    def __init__(self, distance_map: DistanceMap):
        self.distance_map = distance_map

    def build_route(self, start:str, packages:PackageHashMap, target:int) -> list[Package]:
        route = [start]
        visited_ids = {start}
        current = start

        while len(visited_ids) < target:
            next_package = self.find_nearest_package(current, packages, visited_ids)
            if next_package is None:
                break

            route.append(next_package)
            visited_ids.add(next_package.package_id)
            current = next_package.address_w_zip

            '''if next_package.must_be_delivered_with:
                if len(next_package.must_be_delivered_with)
                for pid in next_package.must_be_delivered_with:
                    package = packages.search_package(pid)
                    if pid not in visited_ids:
                        print(package)
                        route.append(package)
                        visited_ids.add(package.package_id)'''
        return route

    def find_nearest_package(self, curr_addr:str, unvisited:PackageHashMap, visited_ids:set):
        closest = float("inf")
        nearest_neighbor = None

        for i,package in enumerate(unvisited.packages_table):
            package = unvisited.packages_table[i]

            if (unvisited.status_table[i] is not SlotStatus.OCCUPIED
                    or package is None
                    or package.package_id in visited_ids
            ):
                continue
            dist = self.distance_map.get_distance(curr_addr, package.address_w_zip)

            if dist < closest:
                closest = dist
                nearest_neighbor = package

        return nearest_neighbor


packages = PackageLoader.load_from_file("../data/packages.csv", PackageHashMap(61, 1, 1, .75))
distances = DistanceMap("../data/distances.csv")
routing = Routing(distances)
route = routing.build_route('HUB',packages, 10)




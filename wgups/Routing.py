from wgups.datastore.DistanceMap import DistanceMap
from wgups.datastore.PackageHashMap import PackageHashMap, SlotStatus
from wgups.dataloader.PackageLoader import PackageLoader


class Routing:
    def __init__(self):
        pass

    def find_nearest_package(self, start, unvisited:PackageHashMap, distance_map:DistanceMap):
        closest = float("inf")
        nearest_neighbor = None
        count = 0
        for i in range(len(unvisited.packages_table)):
            if unvisited.status_table[i] is not SlotStatus.OCCUPIED or unvisited.packages_table[i] == start:
                continue
            dist = distance_map.get_distance(unvisited.packages_table[i].address_w_zip, start.address_w_zip)

            if dist < closest:
                closest = dist
                nearest_neighbor = unvisited.packages_table[i]
        return nearest_neighbor




hash_map = PackageHashMap(61, 1, 1, .75)
packages = PackageLoader.load_from_file("../data/packages.csv", hash_map)
distances = DistanceMap("../data/distances.csv")
routing = Routing()
neighbor = routing.find_nearest_package(packages.search_package(3),packages, distances)
print(neighbor)


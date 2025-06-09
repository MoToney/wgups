import csv
from datetime import datetime, time

from wgups.Routing import Routing
from wgups.TimeManager import TimeManager
from wgups.Truck import Truck
from wgups.dataloader.PackageLoader import PackageLoader
from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.datastore.DistanceMap import DistanceMap


packages = PackageLoader("data/packages.csv",
                                        PackageHashMap(61, 1, 1, .75)).get_map()
distances = DistanceMap("data/distances.csv")
routing = Routing(distances, packages)

distance=0
route_id = 1

#Truck 1

clockies = datetime(1900,1,1,8,0)
clock = TimeManager(clockies)
route, first_time, visited_ids = routing.build_route(1, clockies, set())
package_list = []

for stop in route:
    package_list.append(packages.packages_table[int(stop.package_id)])

truck = Truck(1, 16, distances, clock)
truck.load_packages(package_list)
truck.drive()

#Truck 2
cur_tha_time = datetime(1900,1,1,8,0)
clock = TimeManager(cur_tha_time)
route2, second_time, more_visited_ids = routing.build_route(2, cur_tha_time, visited_ids)
second_package_list = []

for stop2 in route2:
    second_package_list.append(packages.packages_table[int(stop2.package_id)])
truck2 = Truck(2, 16, distances, clock)
truck2.load_packages(second_package_list)
truck2.drive()

first_to_arrive = min(first_time, second_time)
clock = TimeManager(first_to_arrive)
route2, third_time, more_visited_ids = routing.build_route(2, first_to_arrive, visited_ids)
third_package_list = []

for stop2 in route2:
    third_package_list.append(packages.packages_table[int(stop2.package_id)])
truck2 = Truck(2, 16, distances, clock)
truck2.load_packages(third_package_list)
truck2.drive()





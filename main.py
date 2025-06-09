from datetime import datetime, time

from wgups.Routing import Routing
from wgups.TimeManager import TimeManager
from wgups.Truck import Truck
from wgups.dataloader.PackageLoader import PackageLoader
from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.datastore.DistanceMap import DistanceMap

# Maurice Toney Student ID:012549854

packages = PackageLoader("data/packages.csv",
                                        PackageHashMap(61, 1, 1, .75)).get_map()
distoos = DistanceMap("data/distances.csv")
routing = Routing(distoos, packages)

distance=0
route_id = 1

#Truck 1

clockies = datetime(1900,1,1,8,0)
clock = TimeManager(clockies)
route, first_time, first_miles, visited_ids = routing.build_route(1, clockies, set())
package_list = []

for stop in route:
    package_list.append(packages.packages_table[int(stop.package_id)])

truck = Truck(1, 16, distoos, clock)
truck.load_packages(package_list)
truck.drive()

#Truck 2
cur_tha_time = datetime(1900,1,1,8,0)
clock = TimeManager(cur_tha_time)
route2, second_time, second_miles, more_visited_ids = routing.build_route(2, cur_tha_time, visited_ids)
second_package_list = []

for stop2 in route2:
    second_package_list.append(packages.packages_table[int(stop2.package_id)])
truck2 = Truck(2, 16, distoos, clock)
truck2.load_packages(second_package_list)
truck2.drive()

first_to_arrive = min(first_time, second_time)
clock = TimeManager(first_to_arrive)
route2, third_time, third_miles, more_visited_ids = routing.build_route(3, first_to_arrive, visited_ids)
third_package_list = []

for stop2 in route2:
    third_package_list.append(packages.packages_table[int(stop2.package_id)])
truck2 = Truck(2, 16, distoos, clock)
truck2.load_packages(third_package_list)
truck2.drive()

print(second_miles)
total_miles = second_miles + third_miles + first_miles
print(total_miles)





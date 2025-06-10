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
clock1 = TimeManager(clockies)
route, first_time, first_miles, first_visited_ids = routing.build_route(1, clockies, set())
print(first_time)
package_list = []
for stop in route:
    print(stop.package_id, stop.address_w_zip, stop.deadline
          , stop.special_note)
    package_list.append(packages.packages_table[int(stop.package_id)])

print(len(package_list))
print("\n")

truck = Truck(1, 16, distoos, clock1)
truck.load_packages(package_list)
truck.drive()

#Truck 2
cur_tha_time = datetime(1900,1,1,8,0)
clock2 = TimeManager(cur_tha_time)
route2, second_time, second_miles, more_visited_ids = routing.build_route(2, cur_tha_time, first_visited_ids)
second_package_list = []
print(second_time)

for stop2 in route2:
    second_package_list.append(packages.packages_table[int(stop2.package_id)])
    print(stop2)
truck2 = Truck(2, 16, distoos, clock2)
truck2.load_packages(second_package_list)
truck2.drive()


#Truck 3
first_to_arrive = min(first_time, second_time)
clock3 = TimeManager(first_to_arrive)
route3, third_time, third_miles, more_visited_ids = routing.build_route(3, first_to_arrive, more_visited_ids)
third_package_list = []
print("\n")
print(third_time)

for stop3 in route3:
    print(stop3)
    third_package_list.append(packages.packages_table[int(stop3.package_id)])
truck3 = Truck(3, 16, distoos, clock3)
truck3.load_packages(third_package_list)
truck3.drive()


total_miles = second_miles + third_miles + first_miles
print(total_miles)





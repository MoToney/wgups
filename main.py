from datetime import datetime, time

from wgups.Package import Package
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

print("\n")
#Truck 1
clockies = datetime(1900,1,1,8,0)
clock1 = TimeManager(clockies)
route, first_time, first_miles, first_visited_ids = routing.build_route(1, clockies, set())
package_list = []
for stop in route:
    print(stop.package_id, stop.address_w_zip, stop.deadline
          , stop.special_note)
    package_list.append(packages[stop.package_id])


truck1 = Truck(1, 16, distoos, clock1)
truck1.load_packages(package_list)
truck1.drive()
print(first_miles, first_time)
print(len(package_list))

print("\n")
#Truck 2
cur_tha_time = datetime(1900,1,1,8,0)
clock2 = TimeManager(cur_tha_time)
route2, second_time, second_miles, more_visited_ids = routing.build_route(2, cur_tha_time, first_visited_ids)
second_package_list = []

for stop2 in route2:
    second_package_list.append(packages[stop2.package_id])
    print(stop2)
truck2 = Truck(2, 16, distoos, clock2)
truck2.load_packages(second_package_list)
truck2.drive()
print(second_miles, second_time)
print(len(second_package_list))

print("\n")
#Truck 3
first_to_arrive = min(first_time, second_time)
clock3 = TimeManager(first_to_arrive)
route3, third_time, third_miles, many_more_visited_ids = routing.build_route(3, first_to_arrive, more_visited_ids)
third_package_list = []

for stop3 in route3:
    print(stop3)
    third_package_list.append(packages[stop3.package_id])
truck3 = Truck(3, 16, distoos, clock3)
truck3.load_packages(third_package_list)
truck3.drive()
print(third_time, third_miles)
print(len(third_package_list))

if len(many_more_visited_ids) != 40:
    time_for_last_route = max(second_time, datetime(1900,1,1,10,20))
    clock4 = TimeManager(time_for_last_route)
    route4, fourth_time, fourth_miles, max_visited_ids = routing.build_route(4, time_for_last_route, many_more_visited_ids)
    fourth_package_list = []
    print(clock2)

    for stop4 in route4:
        print(stop4)
        fourth_package_list.append(packages[stop4.package_id])
    truck2.load_packages(fourth_package_list)
    truck2.drive()
    print(fourth_time,fourth_miles)
    print(len(third_package_list))


total_miles = second_miles + third_miles + first_miles + fourth_miles
final_time = min(third_time, fourth_time)
print(total_miles, final_time)
print(max_visited_ids)

def get_package_status_at_time(package: Package, query_time: datetime) -> str:
    if query_time < package.departure_time:

        return f"At Hub as of {query_time.time()}"
    elif package.departure_time <= query_time < package.delivery_time:
        return f"En Route as of {query_time.time()}"
    else:
        return f"Delivered at {package.delivery_time.time()}"

def get_all_packages_at_time(query_time: datetime):
    print(f"Status at {query_time.time()}:\n")
    for package in packages.packages_table:
        if isinstance(package, Package):
            print(get_package_status_at_time(package, query_time))

get_all_packages_at_time(datetime(1900,1,1,8,0))

print(f"\nTotal mileage: {first_miles + second_miles + third_miles + fourth_miles}")






from datetime import datetime, time

from wgups.Package import Package
from wgups.Routing import Routing
from wgups.SimulationClock import SimulationClock
from wgups.Truck import Truck
from wgups.dataloader.PackageLoader import PackageLoader
from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.datastore.DistanceMap import DistanceMap

# Maurice Toney Student ID:012549854

CAPACITY = 16

clock = SimulationClock(datetime(1900,1,1,8,0))
packages = PackageLoader("data/packages.csv",
                                        PackageHashMap(61, 1, 1, .75)).get_map()
distoos = DistanceMap("data/distances.csv")
routing = Routing(distoos, packages, clock)

clock.schedule_event(datetime(1900,1,1,9,5), routing.make_available, 6)
clock.schedule_event(datetime(1900,1,1,10,20), routing.update_address, 9)

start_time = datetime(1900,1,1,8,0)
clock.run_until(start_time)

route1, time1, miles1, vis1 = routing.build_route(1, start_time, set())
route2, time2, miles2, vis2 = routing.build_route(2, start_time, vis1)

truck1 = Truck(1, CAPACITY, distoos, clock)
truck2 = Truck(2, CAPACITY, distoos, clock)

clock.schedule_event(start_time, truck1.load_packages, route1)
clock.schedule_event(start_time, truck2.load_packages, route2)

print(miles1, time1, len(route1) , end="\n\n")
print(miles2, time2, len(route2), end="\n\n")

clock.run_until(min(time1, time2))


truck3 = Truck(3, CAPACITY, distoos, clock)
route3, time3, miles3, vis3 = routing.build_route(3, clock.now(), vis2)
clock.schedule_event(clock.now(), truck3.load_packages, route3)
clock.schedule_event(clock.now(), truck3.deliver_package, 0)
print(miles3, time3, len(route3), end="\n\n")


clock.run_until(max(time1, time2, datetime(1900,1,1,10,20)))
if time1 < time2:
    route4, time4, miles4, vis4 = routing.build_route(2, clock.now(), vis3)
    clock.schedule_event(clock.now(), truck2.load_packages, route4)

else:
    route4, time4, miles4, vis4 = routing.build_route(1, clock.now(), vis3)
    clock.schedule_event(clock.now(), truck1.load_packages, route4)

print(miles4, time4, len(route4), end="\n\n")


clock.run_until(datetime(1900,1,1,17,0))

print("\n")
#Truck 3

def get_package_status_at_time(package: Package, query_time: datetime) -> str:

    if package.departure_time is None:
        return f"At Hub as of {query_time.time()}"
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

print(f"\nTotal mileage: {miles1+miles2+miles3+miles4}")


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
print(miles3, time3, len(route3), end="\n\n")


clock.run_until(max(time1, time2, datetime(1900,1,1,10,20)))
if time1 < time2:
    route4, time4, miles4, vis4 = routing.build_route(2, clock.now(), vis3)
    clock.schedule_event(clock.now(), truck2.load_packages, route4)

else:
    route4, time4, miles4, vis4 = routing.build_route(1, clock.now(), vis3)
    clock.schedule_event(clock.now(), truck1.load_packages, route4)

clock.run_until(datetime(1900,1,1,17,0))

def get_package_status_at_time(package: Package, query_time: datetime) -> str:

    if package.available_time and query_time < package.available_time:
        return f"Package {package.package_id}: Not Available as of {query_time.time()}"
    if package.departure_time is None:
        return f"Package {package.package_id}: At Hub as of {query_time.time()}"
    if query_time < package.departure_time:
        return f"Package {package.package_id}: At Hub as of {query_time.time()}"
    elif package.departure_time <= query_time < package.delivery_time:
        return f"Package {package.package_id}: En Route on {package.get_truck_carrier()} as of {query_time.time()}"
    else:
        return f"Package {package.package_id}: Delivered by {package.get_truck_carrier()} at {package.delivery_time.time()}"

def get_all_packages_at_time(query_time: datetime):
    print(f"\n Status at {query_time.time()}:")
    for package in packages.packages_table:
        if isinstance(package, Package):
            print(get_package_status_at_time(package, query_time))

get_all_packages_at_time(datetime(1900,1,1,8,0))
print(miles3)
print(truck3.distance_travelled)
print(f"\nTotal mileage: {miles1+miles2+miles3+miles4}")

while True:
    print("\nWelcome to the WGUPS Menu")
    print("1. Get Delivery Status of a Package at a Specified Time")
    print("2. Get Delivery Status of all Packages at a Specified Time")
    print("3. View Total Miles Travelled by all Trucks")
    print("4. Exit")
    try:
        choice = int(input("Enter a number: "))
        if choice not in (1, 2, 3, 4):
            print("Invalid number, pick a number from 1 to 4")
            continue
    except ValueError:
        print("Invalid input. Please enter a number.")
        continue

    if choice == 1:
        try:
            pid = int(input("Enter Package ID: "))
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue
        p = packages.search_package(pid)
        if p is None:
            print("Package not found")
            continue

        try:
            hour = int(input("Enter the hour in 24hr time (EX: 15 = 3pm): "))
            if hour < 0 or hour > 23:
                print("This is not a valid hour.")
                continue
        except ValueError:
            print("Invalid input. Please enter a number.")

        try:
            minutes = int(input("Enter the number of minutes: "))
            if minutes < 0 or minutes > 59:
                print("This is not a valid number of minutes.")
                continue
        except ValueError:
            print("Invalid input. Please enter a number.")

        qt = datetime(1900,1,1, hour, minutes)
        print(get_package_status_at_time(p, qt))

    if choice == 2:
        try:
            hour = int(input("Enter the hour in 24hr time (EX: 15 = 3pm): "))
            if hour < 0 or hour > 23:
                print("This is not a valid hour.")
                continue
        except ValueError:
            print("Invalid input. Please enter a number.")

        try:
            minutes = int(input("Enter the number of minutes: "))
            if minutes < 0 or minutes > 59:
                print("This is not a valid number of minutes.")
                continue
        except ValueError:
            print("Invalid input. Please enter a number.")

        qt = datetime(1900, 1, 1, hour, minutes)
        print(get_all_packages_at_time(qt))

    if choice == 3:
        print(f"Total miles traveled by all trucks: {truck1.distance_travelled + truck2.distance_travelled + truck3.distance_travelled}")
        print(f"Truck 1 Mileage: {truck1.distance_travelled}")
        print(f"Truck 2 Mileage: {truck2.distance_travelled}")
        print(f"Truck 3 Mileage: {truck3.distance_travelled}")

    if choice == 4:
        print("Program Terminated")
        break







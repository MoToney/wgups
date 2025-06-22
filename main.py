from datetime import datetime
from typing import  Optional

from wgups.Package import Package
from wgups.Routing import Routing
from wgups.SimulationClock import SimulationClock
from wgups.Truck import Truck

from wgups.dataloader.PackageLoader import PackageLoader
from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.datastore.DistanceMap import DistanceMap

# Maurice Toney Student ID:012549854

# Configuration constants
CAPACITY = 16  # Maximum number of packages each truck can carry
START_TIME = datetime(1900, 1, 1, 8, 0)  # Simulation start time (8:00 AM)
END_TIME = datetime(1900, 1, 1, 17, 0)  # Simulation end time (5:00 PM)

# Initialize simulation components
clock = SimulationClock(START_TIME)  # Initialize simulation clock
packages = PackageLoader("data/packages.csv", PackageHashMap(61, 1, 1, .75)).get_map()  # Load packages from CSV
distances = DistanceMap("data/distances.csv")  # Load distance data from CSV
routing = Routing(distances, packages, clock)  # Initialize routing system

# Schedule special events for package availability and address updates
clock.schedule_event(datetime(1900, 1, 1, 9, 5), routing.make_available, 6)  # Make package 6 available at 9:05 AM
clock.schedule_event(datetime(1900, 1, 1, 10, 20), routing.update_address, 9)  # Update package 9's address at 10:20 AM

# Run simulation to start time to process any initial events
clock.run_until(START_TIME)

# Build initial routes for trucks 1 and 2
route1, time1, miles1, dispatched1 = routing.build_route(1, START_TIME, set())  # First truck route
route2, time2, miles2, dispatched2 = routing.build_route(2, START_TIME, dispatched1)  # Second truck route

# Initialize trucks
truck1 = Truck(1, CAPACITY, distances, clock)
truck2 = Truck(2, CAPACITY, distances, clock)

# Schedule package loading events for both trucks
clock.schedule_event(START_TIME, truck1.load_packages, route1)
clock.schedule_event(START_TIME, truck2.load_packages, route2)

# Print initial route statistics
print(f"Truck 1: {miles1:.2f} miles, {time1.strftime('%H:%M')}, {len(route1)} packages")
print(f"Truck 2: {miles2:.2f} miles, {time2.strftime('%H:%M')}, {len(route2)} packages")

# Run simulation until first truck completes delivery
first_completion_time = min(time1, time2)
clock.run_until(first_completion_time)

# Initialize third truck and build its route
truck3 = Truck(3, CAPACITY, distances, clock)
route3, time3, miles3, dispatched3 = routing.build_route(3, clock.now(), dispatched2)
clock.schedule_event(clock.now(), truck3.load_packages, route3)
print(f"Truck 3: {miles3:.2f} miles, {time3.strftime('%H:%M')}, {len(route3)} packages")

# Run simulation until address update time and first two trucks complete
address_update_time = datetime(1900, 1, 1, 10, 20)
simulation_time = max(time1, time2, address_update_time) # start the next route either when the address is updated or when the slower truck has returned to the hub
clock.run_until(simulation_time)

# Build final route for the truck that finished last
if time1 < time2:
    route4, time4, miles4, vis4 = routing.build_route(2, clock.now(), dispatched3) # builds the route for truck 2
    clock.schedule_event(clock.now(), truck2.load_packages, route4) # schedules the event to load the packages for truck 2

# if truck 2 is done delivering before truck 1, build the last route for truck 1
else:
    route4, time4, miles4, vis4 = routing.build_route(1, clock.now(), dispatched3) # builds the route for truck 1
    clock.schedule_event(clock.now(), truck1.load_packages, route4) # schedules the event to load the packages for truck 1

# Run simulation to end of day
clock.run_until(END_TIME)

def get_package_status_at_time(package: Package, query_time: datetime) -> str:
    """
    Returns the status of a package at a specific time.
    
    This function determines the delivery status of a package based on its
    availability time, departure time, and delivery time relative to the query time.
    
    :param package: The package to check status for
    :param query_time: The time to check status at
    :return: A string describing the package status at the specified time
    """
    # Check if package is not yet available (has delayed availability)
    if package.available_time and query_time < package.available_time:
        return f"Package {package.package_id}: Not Available as of {query_time.strftime('%H:%M')}"
    
    # Check if package is still at the hub (hasn't departed yet)
    if package.departure_time is None or query_time < package.departure_time:
        return f"Package {package.package_id}: At Hub as of {query_time.strftime('%H:%M')}"
    
    # Check if package is en route (departed but not yet delivered)
    elif package.departure_time <= query_time < package.delivery_time:
        return f"Package {package.package_id}: En Route on {package.get_truck_carrier()} as of {query_time.strftime('%H:%M')}"
    
    # Check if package has been delivered
    elif package.delivery_time is not None and query_time >= package.delivery_time:
        return f"Package {package.package_id}: Delivered by {package.get_truck_carrier()} at {package.delivery_time.strftime('%H:%M')}"
    
    # Fallback case for unexpected states
    else:
        return f"Package {package.package_id}: Status Unknown as of {query_time.strftime('%H:%M')}"

def get_all_packages_at_time(query_time: datetime) -> None:
    """
    Prints the status of all packages at a specific time.
    
    :param query_time: The time to check all package statuses at
    """
    print(f"\nStatus at {query_time.strftime('%H:%M')}:")
    for package in packages.packages_table:
        if isinstance(package, Package):
            print(get_package_status_at_time(package, query_time))

def get_user_time_input() -> Optional[datetime]:
    """
    Gets time input from user with validation.
    
    :return: datetime object with user input, or None if input is invalid
    """
    try:
        hour = int(input("Enter the hour in 24hr time (EX: 15 = 3pm): "))
        if hour < 0 or hour > 23:
            print("Invalid hour. Please enter a number between 0 and 23.")
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

    try:
        minutes = int(input("Enter the number of minutes: "))
        if minutes < 0 or minutes > 59:
            print("Invalid minutes. Please enter a number between 0 and 59.")
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None

    return datetime(1900, 1, 1, hour, minutes)

def display_total_mileage() -> None:
    """
    Displays total mileage for all trucks and individual truck mileage.
    """
    total_miles = truck1.distance_travelled + truck2.distance_travelled + truck3.distance_travelled
    print(f"Total miles traveled by all trucks: {total_miles:.2f}")
    print(f"Truck 1 Mileage: {truck1.distance_travelled:.2f}")
    print(f"Truck 2 Mileage: {truck2.distance_travelled:.2f}")
    print(f"Truck 3 Mileage: {truck3.distance_travelled:.2f}")

# Display initial status and statistics
get_all_packages_at_time(START_TIME)
print(f"\nTotal mileage: {miles1 + miles2 + miles3 + miles4:.2f}")

# Main menu loop
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
        # Get package ID from user
        try:
            package_id = int(input("Enter Package ID: "))
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue
            
        package = packages.search_package(package_id)
        if package is None:
            print("Package not found")
            continue

        # Get time from user
        query_time = get_user_time_input()
        if query_time is None:
            continue

        print(get_package_status_at_time(package, query_time))

    elif choice == 2:
        # Get time from user
        query_time = get_user_time_input()
        if query_time is None:
            continue

        get_all_packages_at_time(query_time)

    elif choice == 3:
        display_total_mileage()

    elif choice == 4:
        print("Program Terminated")
        break







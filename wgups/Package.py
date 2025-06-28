'''
a.	Has a status to see if delivered, in route, or at hub
b.	Has a specific truck
c.	Has a specific time ready
d.	40 packages in total
e.	Gets loaded into the truck
f.	Gets loaded into the data structure containing all packages

'''

from enum import Enum
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field

class PackageStatus(Enum):
    """
    returns the status of the package throughout the delivery cycle
    """
    NOT_READY = 0
    AT_HUB = 1
    IN_ROUTE = 2
    DELIVERED = 3

    def __str__(self):
        if self.NOT_READY:
            return "Not Available"
        elif self.AT_HUB:
            return "At Hub"
        elif self.IN_ROUTE:
            return "In Route"
        elif self.DELIVERED:
            return "Delivered"
        else:
            return "Unknown Status"

class TruckCarrier(Enum):
    """
    returns the truck that is associated with the object
    """
    NONE = 0
    TRUCK_1 = 1
    TRUCK_2 = 2
    TRUCK_3 = 3

    def __str__(self):
        if self.TRUCK_1:
            return 'Truck 1'
        elif self.TRUCK_2:
            return 'Truck 2'
        elif self.TRUCK_3:
            return 'Truck 3'
        elif self.NONE:
            return 'No Truck Assigned'
        else:
            return 'None'

@dataclass
class Package:
    """
    Represents a package that will be delivered to an address via a truck object

    Attributes:
        package_id (int): The unique identifier for the package
        address (str): The street and house number of the package
        city (str): The city of the package
        zip_code (str): The zip code of the package
        state (str): The state of the package
        deadline (datetime): The time the package must be delivered by
        weight (float): The weight of the package
        note (dict): The note of the package, denoting special handling guidelines
        status (PackageStatus): The status of the package, which is a phase in the PackageStatus Enum
        address_w_zip (str): The address of the package with the zip code
        must_be_delivered_with (list[int] or None): The ids of packages that must be delivered at the same time as the package
        available_time (datetime or None): The time the package is available to be delivered
        required_truck (int or None): The truck that is required to deliver the package
        wrong_address (bool): Whether the package has the wrong address
        packages_at_same_address (Package or None): The package that is at the same address as the current package
        delivery_time (datetime or None): The time the package was delivered
        departure_time (datetime or None): The time the package was loaded onto a truck and left the hub
        truck_carrier (TruckCarrier): The truck that is associated with the package
    """
    package_id: int
    address: str
    city: str
    state: str
    zip_code: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    deadline: Optional[datetime] = None
    weight: Optional[float] = None
    note: str = ""
    status: PackageStatus = PackageStatus.NOT_READY
    must_be_delivered_with: Optional[List[int]] = field(default_factory=list)
    available_time: Optional[datetime] = None
    required_truck: Optional[int] = None
    wrong_address: bool = False
    packages_at_same_address: Optional[List[int]] = field(default_factory=list)
    delivery_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None
    truck_carrier: TruckCarrier = TruckCarrier.NONE

    def __post_init__(self):
        self.address_w_zip = self.address # this is for standardization with the addresses in distances.csv

    def set_address(self, address: str) -> None:
        self.address = address
    def get_address(self) -> str:
        return self.address
    def set_city(self, city: str) -> None:
        self.city = city
    def get_city(self) -> str:
        return self.city
    def set_state(self, state: str) -> None:
        self.state = state
    def get_state(self) -> str:
        return self.state
    def set_zip_code(self, zip_code: str) -> None:
        self.zip_code = zip_code
    def get_zip_code(self) -> str:
        return self.zip_code
    def set_lat(self, lat: float) -> None:
        self.lat = lat
    def get_lat(self) -> float:
        return self.lat
    def set_lon(self, lon: float) -> None:
        self.lon = lon
    def get_lon(self) -> float:
        return self.lon
    def set_deadline(self, deadline: datetime) -> None:
        self.deadline = deadline
    def get_deadline(self) -> datetime:
        return self.deadline
    def set_weight(self, weight: float) -> None:
        self.weight = weight
    def get_weight(self) -> float:
        return self.weight
    def set_note(self, note: str) -> None:
        self.note = note
    def get_note(self) -> str:
        return self.note
    def set_status(self, status: PackageStatus):
        self.status = status
    def get_status(self) -> PackageStatus:
        return self.status
    def set_truck(self, truck: TruckCarrier) -> None:
        self.truck_carrier = truck
    def get_truck(self) -> str:
        """
        Returns string of the truck carrier of the package

        :return: str
        :attribute: truck_carrier: TruckCarrier.TRUCK_1, TruckCarrier.TRUCK_2, TruckCarrier.TRUCK_3, or TruckCarrier.NONE
        """
        return self.truck_carrier
    def set_delivery_time(self, delivery_time: datetime) -> None:
        """
        Sets the delivery time of the package

        :param delivery_time: the time the package was delivered
        :type delivery_time: datetime

        """
        self.delivery_time = delivery_time
    def get_delivery_time(self) -> datetime:
        return self.delivery_time
    def set_departure_time(self, departure_time: datetime) -> None:
        """
        Sets the departure time of the package
        """
        self.departure_time = departure_time
    def get_departure_time(self) -> datetime:
        return self.departure_time
    def get_address_w_zip(self) -> str:
        """
        Returns address that is usable when referencing the listed address for the Package in DistanceMap
        """
        address_w_zip = (f"{self.address}({self.zip_code})")
        return address_w_zip

    def set_address_w_zip(self, address_w_zip: str) -> None:
        """
        Sets the address with zip code of the package
        """
        self.address_w_zip = address_w_zip

    def set_full_address(self, address: str, city: str, state: str, zip_code: str) -> None:
        """
        Sets the full address of the package
        """
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code


    def get_siblings(self) -> list[int]:
        """
        Returns the packages that are at the same address as the current package
        """
        return self.packages_at_same_address

    def set_packages_at_same_address(self, other_packages: list[int]) -> None:
        """
        Sets the packages that are at the same address as the current package
        """
        self.packages_at_same_address = other_packages

    def __str__(self):
        return (f"Package {self.package_id} | "
                f"Address: {self.address}, {self.city}, {self.state}, {self.zip_code} | "
                f"Deadline: {self.deadline.strftime('%I:%M %p') if self.deadline else 'N/A'} | "
                f"Weight: {self.weight} | "
                f"Note: {self.note if self.note else 'N/A'} | ")

    def __eq__(self, other) -> bool:
        if not isinstance(other, Package):
            return NotImplemented
        return self.package_id == other.package_id

    def __hash__(self):
        return hash(self.package_id)



"""package = Package(2, "2510 South Vernice Drive", "Copperas Cove", "76522", "Utah", deadline=datetime.now(), weight=3.0,
                  note="",status=PackageStatus.NOT_READY)
print(package)"""

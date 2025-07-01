
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
        status (PackageStatus): The status of the package, which is a phase in the PackageStatus Enun
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

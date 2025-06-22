from datetime import datetime
from enum import Enum
from typing import Optional

from wgups.Package import Package, PackageStatus


class SlotStatus(Enum):
    """
    This class is used to store the status of a slot in the package hash map.
    """
    EMPTY = 0 # the slot is empty
    OCCUPIED = 1 # the slot is occupied
    DELETED = 2


class PackageHashMap:
    """
    This class is used to store the packages in the hash map.
    """
    def __init__(self, size: int, c1:int = 1, c2:int = 1, load_factor:float = .75):
        """
        Initializes the PackageHashMap class.
        """
        self.size = size # the size of the hash map
        self.c1 = c1 # the first constant for quadratic probing
        self.c2 = c2 # the second constant for quadratic probing
        self.packages_table = [None] * self.size # the table of packages
        self.status_table = [SlotStatus.EMPTY] * self.size # the table of statuses
        self.load_factor = load_factor # the load factor of the hash map
        self.num_items = 0

    def hash_key(self, key:int) -> int:
        """
        Returns the hash key for a given package id.
        """
        hashkey = hash(key) % self.size # hashes the package id and takes the modulus of the size of the hash map
        return hashkey

    def quadratic_hash_key(self, key:int, i:int) -> int:
        """
        Returns the quadratic hash key for a given package id.
        """
        quad_hashkey = (hash(key) + self.c1 * i + self.c2 * i * i) % self.size # hashes the package id and takes the modulus of the size of the hash map
        return quad_hashkey

    def is_package(self, i:int) -> bool:
        """
        Returns True if the slot is occupied by a package, False otherwise.
        """
        return isinstance(self.packages_table[i], Package)


    def add_package(self, package: Package):
        """
        Adds a package to the hash map.
        """
        i = 0 # the index of the slot
        buckets_probed = 0 # the number of buckets probed

        # hash function determines initial bucket
        bucket = self.hash_key(package.package_id) # hashes the package id and takes the modulus of the size of the hash map
        while buckets_probed < self.size: # while the number of buckets probed is less than the size of the hash map

            # insert item in next empty bucket
            if self.status_table[bucket] is SlotStatus.EMPTY:
                self.packages_table[bucket] = package
                self.status_table[bucket] = SlotStatus.OCCUPIED
                self.num_items += 1

                # if the load factor is reached, resize the hash map
                if float(self.num_items/self.size) >= self.load_factor:
                    self.resize() # resize the hash map
                return True

            # increment i and recompute bucket index
            # c1 and c2 are programmer-defined constants for quadratic probing
            i += 1 # increment the index of the slot
            bucket = self.quadratic_hash_key(package.package_id, i) # hashes the package id and takes the modulus of the size of the hash map

            # increment number of buckets probed
            buckets_probed += 1

        return False

    def search_package(self, key: int) -> Optional[Package]:
        """
        Searches for a package in the hash map.
        """
        i = 0
        buckets_probed = 0

        # hash function determines initial bucket
        bucket = self.hash_key(key)

        # while the slot is not empty and the number of buckets probed is less than the size of the hash map
        while self.status_table[bucket] is not SlotStatus.EMPTY and buckets_probed < self.size:

            # if the slot is occupied by a package and the package id is the same as the key, return the package
            if self.status_table[bucket] is SlotStatus.OCCUPIED and self.packages_table[bucket].package_id == key:
                return self.packages_table[bucket]

            # increment i and recompute bucket instance
            i += 1
            bucket = self.quadratic_hash_key(key, i)

            # increment number of buckets probed
            buckets_probed += 1

        return None

    def remove_package(self, key):
        """
        Removes a package from the hash map.
        """
        i = 0 
        buckets_probed = 0

        # hash function determines initial bucket
        bucket = self.hash_key(key)

        # while the slot is not empty and the number of buckets probed is less than the size of the hash map
        while self.status_table[bucket] is not SlotStatus.EMPTY and buckets_probed < self.size:

            # if the slot is occupied by a package and the package id is the same as the key, remove the package
            if self.status_table[bucket] is SlotStatus.OCCUPIED and self.packages_table[bucket].package_id == key:
                self.packages_table[bucket] = None
                self.status_table[bucket] = SlotStatus.DELETED
                self.num_items -= 1
                return True

            # increment i and recompute bucket index
            i += 1
            bucket = self.quadratic_hash_key(key, i)

            # increment number of buckets probed
            buckets_probed += 1

        return False


    def resize(self):
        """
        Resizes the hash map.
        """
        # save the old packages table, status table, and size
        old_packages_table = self.packages_table
        old_status_table = self.status_table
        old_size = self.size # save the old size

        # double the size of the hash map
        self.size = old_size * 2
        # create a new packages table with the new size
        self.packages_table = [None] * self.size
        # create a new status table with the new size
        self.status_table = [SlotStatus.EMPTY] * self.size
        # reset the number of items
        self.num_items = 0

        # for each slot in the old hash map
        for i in range(old_size):
            # if the slot is occupied, add the package to the new hash map
            if old_status_table[i] == SlotStatus.OCCUPIED:
                self.add_package(old_packages_table[i]) # add the package to the new hash map

    def __str__(self):
        """
        Returns a string representation of the hash map.
        """
        count = self.num_items # get the number of items
        preview_packages = list(self.packages_table)[:3] # get the first three packages
        return (f"PackageHashMap with {count} packages "
                f"(sample packages: {', '.join(map(str, preview_packages))})")

    def __iter__(self):
        """
        Returns an iterator over the hash map.
        """
        # for each package and status in the hash map
        for package, status in zip(self.packages_table, self.status_table):
            # if the slot is occupied and the package is a package, yield the package
            if status == SlotStatus.OCCUPIED and isinstance(package, Package):
                yield package

    def __getitem__(self, key: int) -> Package:
        """
        Returns the package with the given key.
        """
        result = self.search_package(key) # search for the package with the given key
        if result is None: # if the package is not found, raise a KeyError
            raise KeyError(key)
        return result




packages = PackageHashMap(40)
packages.add_package(
    Package(2, "2510 Vernice Drive", "Copperas Cove", "76522", "Utah", deadline=datetime.now(), weight=3.0, note="",
            status=PackageStatus.NOT_READY))
packages.search_package(2)
packages.remove_package(2)

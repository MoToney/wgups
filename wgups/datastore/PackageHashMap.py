from datetime import datetime
from enum import Enum

from wgups.Package import Package, PackageStatus


class SlotStatus(Enum):
    EMPTY = 0
    OCCUPIED = 1
    DELETED = 2


class PackageHashMap:
    def __init__(self, size: int, c1:int = 1, c2:int = 1, load_factor:float = .75):
        self.size = size
        self.c1 = c1
        self.c2 = c2
        self.packages_table = [None] * self.size
        self.status_table = [SlotStatus.EMPTY] * self.size
        self.load_factor = load_factor
        self.num_items = 0

    def hash_key(self, key):
        hashkey = hash(key) % self.size
        return hashkey

    def quadratic_hash_key(self, key, i):
        quad_hashkey = (hash(key) + self.c1 * i + self.c2 * i * i) % self.size
        return quad_hashkey

    def is_package(self,i):
        if isinstance(self.packages_table[i], Package):
            pass
        pass


    def add_package(self, package: Package):
        i = 0
        buckets_probed = 0

        # hash function determines initial bucket
        bucket = self.hash_key(package.package_id)
        while buckets_probed < self.size:

            # insert item in next empty bucket
            if self.status_table[bucket] is SlotStatus.EMPTY:
                self.packages_table[bucket] = package
                self.status_table[bucket] = SlotStatus.OCCUPIED
                self.num_items += 1
                if float(self.num_items/self.size) >= self.load_factor:
                    self.resize()
                return True

            # increment i and recompute bucket index
            # c1 and c2 are programmer-defined constants for quadratic probing
            i += 1
            bucket = self.quadratic_hash_key(package.package_id, i)

            # increment number of buckets probed
            buckets_probed += 1

        return False

    def search_package(self, key):
        i = 0
        buckets_probed = 0

        # hash function determines initial bucket
        bucket = self.hash_key(key)

        while self.status_table[bucket] is not SlotStatus.EMPTY and buckets_probed < self.size:
            if self.status_table[bucket] is SlotStatus.OCCUPIED and self.packages_table[bucket].package_id == key:
                return self.packages_table[bucket]

            # increment i and recompute bucket instance
            i += 1
            bucket = self.quadratic_hash_key(key, i)

            # increment number of buckets probed
            buckets_probed += 1

        return None

    def remove_package(self, key):
        i = 0
        buckets_probed = 0

        # hash function determines initial bucket
        bucket = self.hash_key(key)

        while self.status_table[bucket] is not SlotStatus.EMPTY and buckets_probed < self.size:
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

        old_packages_table = self.packages_table
        old_status_table = self.status_table
        old_size = self.size

        self.size = old_size * 2
        self.packages_table = [None] * self.size
        self.status_table = [SlotStatus.EMPTY] * self.size
        self.num_items = 0

        for i in range(old_size):
            if old_status_table[i] is SlotStatus.OCCUPIED:
                self.add_package(old_packages_table[i])

    def __str__(self):
        count = self.num_items
        preview_packages = list(self.packages_table)[:3]
        return (f"PackageHashMap with {count} packages "
                f"(sample packages: {', '.join(map(str, preview_packages))})")



packages = PackageHashMap(40)
packages.add_package(
    Package(2, "2510 Vernice Drive", "Copperas Cove", "76522", "Utah", deadline=datetime.now(), weight=3.0, note="",
            status=PackageStatus.NOT_READY))
packages.search_package(2)
packages.remove_package(2)

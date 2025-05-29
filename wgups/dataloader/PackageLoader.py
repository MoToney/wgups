from wgups.datastore.PackageHashMap import PackageHashMap
from wgups.Package import Package, PackageStatus
from datetime import datetime
from typing import Optional


class PackageLoader(object):

    @staticmethod
    def load_from_file(file: str, package_hash_map: PackageHashMap) -> Optional[PackageHashMap]:
        import csv
        with open(file, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            header = next(reader)
            print(f"Header: {header}")
            for row in reader:
                if row:
                    package_hash_map.add_package(PackageLoader.csv_to_package(row=row))
            return package_hash_map

    @staticmethod
    def csv_to_package(row: list[str]) -> Package:
        package_id = int(row[0])
        address = row[1]
        city = row[2]
        state = row[3]
        zip_code = row[4]
        deadline = PackageLoader.parse_deadline(row[5])
        weight = float(row[6])
        special_notes = row[7]
        status = PackageStatus.NOT_READY

        return Package(
            package_id=package_id, address=address, city=city, state=state, zip_code=zip_code,
            deadline=deadline, weight=weight, note=special_notes, status=status)

    @staticmethod
    def parse_deadline(deadline_str) -> Optional[datetime]:
        print(f"Parsing deadline: '{deadline_str}'")
        if deadline_str.strip().upper() == 'EOD':
            return None

        try:
            return datetime.strptime(deadline_str.strip(),'%I:%M %p')
        except ValueError:
            raise ValueError('Invalid deadline string')

#test

hash_map = PackageHashMap(40,1,1,.75)
package_loader = PackageLoader()
package_loader.load_from_file("../../data/packages.csv", hash_map)
print(hash_map)

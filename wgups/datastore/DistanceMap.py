class DistanceMap(object):
    def __init__(self, file:str):
        self.addresses = []
        self.matrix = []
        self.address_to_index = {}
        self.load_from_file(self,file)

    @staticmethod
    def load_from_file(self,file: str):
        import csv
        with open(file, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            self.addresses = next(reader)[1:]

            for i, row in enumerate(reader):
                distances = [float(cell) if cell else 0.0 for cell in row[1:]]
                self.matrix.append(distances)
                self.address_to_index[row[0].strip()] = i

    def get_distance(self, addr1: str, addr2: str):
        i = self.address_to_index[addr1]
        j = self.address_to_index[addr2]
        return self.matrix[max(i, j)][min(i, j)]

    def __str__(self):
        sample = []
        max_pairs = 3
        for i in range(min(max_pairs, len(self.addresses))):
            for j in range(i + 1, min(i + 1 + max_pairs, len(self.addresses))):
                a1 = self.addresses[i]
                a2 = self.addresses[j]
                dist = self.get_distance(a1, a2)
                sample.append(f"{a1} -> {a2}: {dist:.2f} mi")

        return (f"DistanceMap with {len(self.addresses)} addresses\n"
                f"Sample distances:\n" + "\n".join(sample))







class DistanceMap:
    """
    This class is used to store the distance map of the addresses.
    """
    def __init__(self, file:str):
        self.addresses = [] # list of addresses
        self.matrix = [] # matrix of distances
        self.file = file # file containing the distance map
        self.load_from_file() # loads the distance map from the file


    def load_from_file(self):
        """
        Loads the distance map from the file.
        """
        import csv
        with open(self.file, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')
            self.addresses = next(reader)[1:]

            for i, row in enumerate(reader):
                distances = [float(cell) if cell else 0.0 for cell in row[1:]] # converts the distances to floats
                self.matrix.append(distances) # adds the distances to the matrix

    def get_distance(self, addr1: str, addr2: str):
        """
        Returns the distance between two addresses.
        """
        i = self.get_index(addr1) # gets the index of the first address
        j = self.get_index(addr2) # gets the index of the second address
        return self.matrix[max(i, j)][min(i, j)] # returns the distance between the two addresses

    def get_index(self, addr: str) -> int | None:
        """
        Returns the index of the address within the matrix.
        :param addr:
        :return: int
        """
        for i, row in enumerate(self.addresses):
            if row == addr:
                return i
        return None

    def __str__(self):
        """
        Returns a string representation of the distance map.
        """
        sample = [] # initializes an empty list
        max_pairs = 3 # maximum number of pairs to sample
        for i in range(min(max_pairs, len(self.addresses))):
            for j in range(i + 1, min(i + 1 + max_pairs, len(self.addresses))):
                a1 = self.addresses[i] # gets the first address
                a2 = self.addresses[j] # gets the second address
                dist = self.get_distance(a1, a2) # gets the distance between the two addresses
                sample.append(f"{a1} -> {a2}: {dist:.2f} mi")

        return (f"DistanceMap with {len(self.addresses)} addresses\n"
                f"Sample distances:\n" + "\n".join(sample))







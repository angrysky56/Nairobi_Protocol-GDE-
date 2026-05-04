from phonological import compare, universal_geometric_hash

def main():
    var apple = universal_geometric_hash("Apple")
    var apples = universal_geometric_hash("Apples")
    var orbit = universal_geometric_hash("Orbit")

    print("apple_apples_distance", apple.distance(apples))
    print("apple_orbit_distance", apple.distance(orbit))
    print("portable engine bootstrap complete")

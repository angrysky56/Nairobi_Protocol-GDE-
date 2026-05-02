from phonological import compare, universal_geometric_hash


fn main():
    let apple = universal_geometric_hash("Apple")
    let apples = universal_geometric_hash("Apples")
    let orbit = universal_geometric_hash("Orbit")

    print("apple_apples_distance", apple.distance(apples))
    print("apple_orbit_distance", apple.distance(orbit))
    print("portable engine bootstrap complete")


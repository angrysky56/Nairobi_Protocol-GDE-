from phonological import compare


fn main():
    let pairs = [
        ("Apple", "Apples"),
        ("Apple", "Orbit"),
        ("Neural", "Logic"),
        ("Sensor", "Sensors"),
    ]

    print("Integration benchmark harness")
    for pair in pairs:
        print(pair[0], pair[1], compare(pair[0], pair[1]))


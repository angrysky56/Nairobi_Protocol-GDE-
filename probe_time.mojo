import std.time
import time

def main():
    print("--- Library Probe ---")
    try:
        var t1 = std.time.now()
        print("Success: std.time.now()")
    except:
        print("Fail: std.time.now()")

    try:
        var t2 = time.time.now()
        print("Success: time.time.now()")
    except:
        print("Fail: time.time.now()")
        
    # Final fallback: Performance Counter
    var t3 = std.time.perf_counter()
    print("Success: std.time.perf_counter() ->", t3)

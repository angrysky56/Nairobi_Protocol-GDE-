from phonological import HashVector
from std.collections import List
from std.os import stat

struct GatewayStore:
    var vault_path: String
    var index_path: String

    def __init__(out self, vault_path: String):
        self.vault_path = vault_path
        self.index_path = vault_path + ".idx"

    def save_vector(self, word: String, vector: HashVector) raises:
        var offset = 0
        try:
            # Use OS stat to get file size (The "Systems" way)
            offset = Int(stat(self.vault_path).st_size)
        except:
            offset = 0

        with open(self.vault_path, "a") as f:
            f.write(word + ":" )
            for i in range(24):
                f.write(String(vector.data[i]))
                if i < 23: f.write(",")
            f.write("\n")

        with open(self.index_path, "a") as idx:
            idx.write(word + ":" + String(offset) + "\n")

    def load_vector_indexed(self, target_word: String) raises -> HashVector:
        var offset = -1
        with open(self.index_path, "r") as idx:
            var lines = idx.read().split("\n")
            for i in range(len(lines)):
                var line = lines[i]
                if not line: continue
                var parts = line.split(":")
                if parts[0] == target_word:
                    offset = Int(parts[1])
                    break
        
        if offset == -1:
            raise Error("Word not found in Index")

        with open(self.vault_path, "r") as f:
            # Explicitly cast to UInt64 and ignore the return value of seek
            _ = f.seek(UInt64(offset))
            
            # Since we can't use read_line, we read a large enough chunk
            # and take the first line. 1024 bytes is safe for a 24D vector.
            var chunk = f.read(1024)
            var target_line = chunk.split("\n")[0]
            
            var parts = target_line.split(":")
            var vec_data = parts[1].split(",")
            
            var vector = HashVector()
            for j in range(24):
                vector.data[j] = Float64(vec_data[j])
            return vector

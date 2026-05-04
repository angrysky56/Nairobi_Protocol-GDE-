struct AtlasPage:
    var offset: UInt64
    var length: UInt64
    var generation: UInt32
    var reserved: UInt32

    def __init__(out self, offset: UInt64 = 0, length: UInt64 = 0):
        self.offset = offset
        self.length = length
        self.generation = 0
        self.reserved = 0

struct AtlasManager:
    var open_pages: Int

    def __init__(out self):
        self.open_pages = 0

    def map_subgraph(mut self, offset: UInt64, length: UInt64) -> AtlasPage:
        self.open_pages += 1
        return AtlasPage(offset=offset, length=length)

    def release_subgraph(mut self, _: AtlasPage):
        if self.open_pages > 0:
            self.open_pages -= 1

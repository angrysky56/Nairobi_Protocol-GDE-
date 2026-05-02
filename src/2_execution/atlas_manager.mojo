@align(32)
struct AtlasPage:
    var offset: UInt64
    var length: UInt64
    var generation: UInt32
    var reserved: UInt32

    fn __init__(inout self, offset: UInt64 = 0, length: UInt64 = 0):
        self.offset = offset
        self.length = length
        self.generation = 0
        self.reserved = 0


struct AtlasManager:
    var open_pages: Int

    fn __init__(inout self):
        self.open_pages = 0

    fn map_subgraph(inout self, offset: UInt64, length: UInt64) -> AtlasPage:
        self.open_pages += 1
        return AtlasPage(offset=offset, length=length)

    fn release_subgraph(inout self, _: AtlasPage):
        if self.open_pages > 0:
            self.open_pages -= 1


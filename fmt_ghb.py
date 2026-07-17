from math import pi, sin, cos, atan2, acos
from .utils import AnyStruct
import numpy as np
import struct

def string_from_bytes(b):
    return b.rstrip(b'\0').decode('utf-8', errors='ignore')

def string_to_bytes(s):
    return s.encode('utf-8')

Header = AnyStruct('Header', (
    ('magic', 'i'),             # +0x00: 0x198237FE 
    ('data_offset', 'i'),       # +0x04: offset to data section
    ('total_size', 'i'),        # +0x08: file/data block size
    ('version', 'i'),           # +0x0C: 0x033FB1A3 (format version)
    ('header_size', 'i'),       # +0x10: 0x4A (74)
    ('reserved_14', 'i'),       # +0x14: always 0
    ('path_length', 'i'),       # +0x18: this is actually the length of the path
                                # +0x1C: this is the path
))

# From the path itself, start here
ExtHeader = AnyStruct('ExtHeader', (
    ('bone_count', 'i'),        # +0x00: bone/mesh count
    ('anim_count', 'i'),        # +0x04: this has to be the animation count
    ('scale', 'f'),             # +0x14: float — scale or bounding radius (100.0 / 200.0)
))

Animations = []

# We'll parse these a little differently
class Animation:
    anim_length : int   # +0x00: This is the length of the animation name
    anim_name : str     # +0x04: This is the animation name
    num_events : int    # +0x04 + anim_length: Number of events
    frame_start : int   # +0x08 + anim_length: Number of events
    frame_count : int   # +0x0C + anim_length: Number of events
                        # We skip the next 16 bytes, for now
    Events = []         # Array of events
    
    def __init__(self, file):
        # Get the length of the animation name here
        self.anim_length = int.from_bytes(file.read(4), byteorder='little')
        self.anim_name = file.read(self.anim_length).decode('utf-8', errors='ignore')
        self.num_events = int.from_bytes(file.read(4), byteorder='little')
        print("Animation name:", self.anim_name)
        
        # TODO process events
        for x in range(self.num_events):
            # We need to add the offset for the last stuff we processed
            newEvent = Event(file)
            self.Events.append(newEvent)
             
        # Modify the start/end states
        self.frame_start = file.read(4)
        self.frame_count = file.read(4)

class Event:
    event_timemul : int     # +0x00: This appears to be an integer for our event time
    event_timedec : int     # +0x04: This appears to be a float multiplier for the event time
    event_length : int      # +0x08: This is the length of the event string
    event_name : str        # +0x0C: This is the event string
    arg_length : int        # +0x0C + event_length: This is the length of the argument
    event_arg : str         # +0x10 + event_length: This is the event argument as a string   
    
    def __init__(self, file):
        # Get the basics of the event here
        self.event_timemul = int.from_bytes(file.read(4), byteorder='little')
        self.event_timedec = int.from_bytes(file.read(4), byteorder='little')
        
        # Now advance the reader past these bytes
        self.event_length = int.from_bytes(file.read(4), byteorder='little')
        self.event_name = file.read(self.event_length).decode('utf-8', errors='ignore')
        self.arg_length = int.from_bytes(file.read(4), byteorder='little')
        
        # Check if the argument length is greater than 0. If so, parse the argument
        if self.arg_length > 0:
            self.event_arg = file.read(self.arg_length).decode('utf-8', errors='ignore')
        
# I really am not sure what this is, but I've found that for most, if not all models this is all the same
class Unknown1Collection:
    quantity : int                      # +0x00: This is the number of tags
    garbage = []                        # Store these in an array
    
    def __init__(self, file):
        # Get the quantity from this file. This is starting to look a lot to me like the number of children objects
        self.quantity = int.from_bytes(file.read(4), byteorder='little')
        
        for x in range(self.quantity):
            newItem = UnknownItem1(file)
            self.garbage.append(newItem)
            
class UnknownItem1:
    len_var1 : int                      # +0x04: length of variable
    var1_name : str                     # +0x08: name of the variable
    var2 : int                          # +0x0E: unknown, but does something
    len_var3 : int                      # +0x12 + len_var1: length of variable
    var3_name : str                     # +0x16 + len_var1: name of the variable
    
    def __init__(self, file):
        # Read this variable, dunno what this is
        self.len_var1 = int.from_bytes(file.read(4), byteorder='little')
        self.var1_name = file.read(self.len_var1).decode('utf-8', errors='ignore')
        
        # I need to read 6, useless bytes
        file.read(6)
        
        # No idea what this is, but I should track it
        self.var2 = int.from_bytes(file.read(4), byteorder='little')
        
        # Read this variable, dunno what this is
        self.len_var3 = int.from_bytes(file.read(4), byteorder='little')
        self.var3_name = file.read(self.len_var3).decode('utf-8', errors='ignore')
        
        # Seems to always read 210 bytes, not sure what these are yet
        # The first 160 seem to be worthless, but I would love to know what the next 50 are
        file.read(210)
        
        # I think we can wrap it, here
        
    
GHB_MAGIC = 0x198237FE 
GHB_VERSION = 0x033FB1A3
GHB_HEADER_SIZE = 0x4A

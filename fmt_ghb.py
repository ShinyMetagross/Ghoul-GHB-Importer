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
    ('frame_count', 'i'),       # +0x00: total animation frame count
    ('anim_count', 'i'),        # +0x04: this has to be the animation count
))

AnimatedModel : bool
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
        #print("Animation name:", self.anim_name)
        
        # TODO process events
        for x in range(self.num_events):
            # We need to add the offset for the last stuff we processed
            newEvent = Event(file)
            self.Events.append(newEvent)
             
        # Modify the start/end states
        self.frame_start = int.from_bytes(file.read(4), byteorder='little')
        self.frame_count = int.from_bytes(file.read(4), byteorder='little')

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
        file.seek(file.tell() + 6)
        
        # No idea what this is, but I should track it
        self.var2 = int.from_bytes(file.read(4), byteorder='little')
        
        # Read this variable, dunno what this is
        self.len_var3 = int.from_bytes(file.read(4), byteorder='little')
        self.var3_name = file.read(self.len_var3).decode('utf-8', errors='ignore')
        
        # Seems to always read 210 bytes, not sure what these are yet
        # The first 160 seem to be worthless, but I would love to know what the next 50 are
        file.seek(file.tell() + 210)
        
        # I think we can wrap it, here

# My data suggests that we need a quantity here
class BoltOnTree:
   num_children : int              # +0x00: number of children in the tree
   children = []
   
   def __init__(self, file, animated):
        self.num_children = int.from_bytes(file.read(4), byteorder='little')
        
        for x in range(self.num_children):
            newBoltOn = BoltOn(file, animated)
            self.children.append(newBoltOn)
   
# Bolton objects have no geometry. I've found that consistently before the actual geometric objects, a constant 9e15dc05 appears
# However, after the name of the bolton appears 104 bytes consistently, though I'm not sure what all they do...
class BoltOn:
    bolton_length : int             # +0x00: length of the bolton name
    bolton_name : str               # +0x04: bolton name
    flags : bytes                   # +0x04 + bolton_length: Flags
    bone_id : int                   # calculate eventually
        
    def __init__(self, file, animated):
        self.bolton_length = int.from_bytes(file.read(4), byteorder='little')
        self.bolton_name = file.read(self.bolton_length).decode('utf-8', errors='ignore')
        # Appears to be padding
        file.seek(file.tell() + 4)
            
        # Read flags
        self.flags = struct.unpack('<h', file.read(2))[0]
        
        # More padding
        file.seek(file.tell() + 5)
        
        # Init some vectors/matrices
        self.local_position = np.empty(3, dtype=float) 
        self.local_scale = np.empty(3, dtype=float)
        self.local_rotation = np.empty(3, dtype=float)
        self.inv_rotation = np.empty(3, dtype=float)
        self.absolute_position = np.empty(3, dtype=float)
        self.transform_matrix = np.empty((3,4), dtype=float)
        
        #print("BoltOn name:", self.bolton_name)
        
        # If the model is animated
        if animated:
            # Raw Local Reference Translation (Pre-Matrix Multiplier)
            self.local_position[0] = struct.unpack('<f', file.read(4))[0]
            self.local_position[1] = struct.unpack('<f', file.read(4))[0]
            self.local_position[2] = struct.unpack('<f', file.read(4))[0]
            
            # Local Bounding Scale Multipliers 
            self.local_scale[0] = struct.unpack('<f', file.read(4))[0]
            self.local_scale[1] = struct.unpack('<f', file.read(4))[0]
            self.local_scale[2] = struct.unpack('<f', file.read(4))[0]
            
            # Rotation in the form of XYZ
            self.local_rotation[0] = struct.unpack('<f', file.read(4))[0]
            self.local_rotation[1] = struct.unpack('<f', file.read(4))[0]
            self.local_rotation[2] = struct.unpack('<f', file.read(4))[0]
            
            # Kinematic Data Separator Tag
            file.seek(file.tell() + 4)
            
            # Runtime Inverse Optimizers (1 / Euler angles) 
            self.inv_rotation[0] = struct.unpack('<f', file.read(4))[0]
            self.inv_rotation[1] = struct.unpack('<f', file.read(4))[0]
            self.inv_rotation[2] = struct.unpack('<f', file.read(4))[0]
            
            # Absolute World Pivot Origin Vector
            self.local_position[0] = struct.unpack('<f', file.read(4))[0]
            self.local_position[1] = struct.unpack('<f', file.read(4))[0]
            self.local_position[2] = struct.unpack('<f', file.read(4))[0]
            
            # Parent Bone Array Index Number   
            self.bone_id = int.from_bytes(file.read(4), byteorder='little')/856
        else:
            # Local Reference Translation (X, Y, Z Position)
            self.local_position[0] = struct.unpack('<f', file.read(4))[0]
            self.local_position[1] = struct.unpack('<f', file.read(4))[0]
            self.local_position[2] = struct.unpack('<f', file.read(4))[0]
            
            # Bounding Box Extents Vector (Width, Length, Height)
            self.local_scale[0] = struct.unpack('<f', file.read(4))[0]
            self.local_scale[1] = struct.unpack('<f', file.read(4))[0]
            self.local_scale[2] = struct.unpack('<f', file.read(4))[0]
            
            # Matrix Marker/Flag** (01 20 20 80) 
            file.seek(file.tell() + 9)
            
            # 3x4 Linear Transformation Matrix (Rotation/Basis)
            self.transform_matrix[0][0] = struct.unpack('<f', file.read(4))[0]
            self.transform_matrix[0][1] = struct.unpack('<f', file.read(4))[0]
            self.transform_matrix[0][2] = struct.unpack('<f', file.read(4))[0]
            self.transform_matrix[0][3] = struct.unpack('<f', file.read(4))[0]
            
            self.transform_matrix[1][0] = struct.unpack('<f', file.read(4))[0]
            self.transform_matrix[1][1] = struct.unpack('<f', file.read(4))[0]
            self.transform_matrix[1][2] = struct.unpack('<f', file.read(4))[0]
            self.transform_matrix[1][3] = struct.unpack('<f', file.read(4))[0]
            
            self.transform_matrix[2][0] = struct.unpack('<f', file.read(4))[0]
            self.transform_matrix[2][1] = struct.unpack('<f', file.read(4))[0]
            self.transform_matrix[2][2] = struct.unpack('<f', file.read(4))[0]
            self.transform_matrix[2][3] = struct.unpack('<f', file.read(4))[0]
            
            # Absolute Reference Translation (X, Y, Z Position)
            self.absolute_position[0] = struct.unpack('<f', file.read(4))[0]
            self.absolute_position[1] = struct.unpack('<f', file.read(4))[0]
            self.absolute_position[2] = struct.unpack('<f', file.read(4))[0]
            
            # Matrix Marker/Flag** (01 20 20 80) 
            file.seek(file.tell() + 4)
     
# My data suggests that we need a quantity here
class ObjectTree:
   num_children : int              # +0x00: number of children in the tree
   children = []
   
   def __init__(self, file):
        self.num_children = int.from_bytes(file.read(4), byteorder='little')
        
        for x in range(self.num_children):
            newObject = MeshObject(file)
            self.children.append(MeshObject)

# Data structure for each mesh object
class MeshObject:
    object_length : int             # +0x00: length of the object name
    object_name : str               # +0x04: object name
    flags : bytes                   # +0x04 + object_length: Flags
    
    def __init__(self, file):
        self.object_length = int.from_bytes(file.read(4), byteorder='little')
        self.object_name = file.read(self.object_length).decode('utf-8', errors='ignore')
        
        #print("Object name:", self.object_name)
        # Appears to be padding
        file.seek(file.tell() + 4)
            
        # Read flags
        self.flags = struct.unpack('<h', file.read(2))[0]
        
        # More padding
        file.seek(file.tell() + 5)
        
        # Init some vectors/matrices
        self.local_position = np.empty(3, dtype=float) 
        self.local_scale = np.empty(3, dtype=float)
        self.local_rotation = np.empty(3, dtype=float)
        self.derived_offset = np.empty(3, dtype=float) 
        self.transform_matrix = np.empty((3,3), dtype=float)
        self.world_reference = np.empty(3, dtype=float) 
        
        # Local Translation Vector
        self.local_position[0] = struct.unpack('<f', file.read(4))[0]
        self.local_position[1] = struct.unpack('<f', file.read(4))[0]
        self.local_position[2] = struct.unpack('<f', file.read(4))[0]
        
        # Derived offset cache. Not sure about the point of this
        self.derived_offset[0] = struct.unpack('<f', file.read(4))[0]
        self.derived_offset[1] = struct.unpack('<f', file.read(4))[0]
        self.derived_offset[2] = struct.unpack('<f', file.read(4))[0]
        
        # More garbage padding
        file.seek(file.tell() + 5)
        #print("cursor position:", hex(file.tell()))
        
        # 3x3 Linear Transformation Matrix (Rotation/Basis)
        self.transform_matrix[0][0] = struct.unpack('<f', file.read(4))[0]
        self.transform_matrix[0][1] = struct.unpack('<f', file.read(4))[0]
        self.transform_matrix[0][2] = struct.unpack('<f', file.read(4))[0]
        
        self.transform_matrix[1][0] = struct.unpack('<f', file.read(4))[0]
        self.transform_matrix[1][1] = struct.unpack('<f', file.read(4))[0]
        self.transform_matrix[1][2] = struct.unpack('<f', file.read(4))[0]
        
        self.transform_matrix[2][0] = struct.unpack('<f', file.read(4))[0]
        self.transform_matrix[2][1] = struct.unpack('<f', file.read(4))[0]
        self.transform_matrix[2][2] = struct.unpack('<f', file.read(4))[0]
        
        # More padding
        file.seek(file.tell() + 4)
        
        # World Reference Cache
        self.local_position[0] = struct.unpack('<f', file.read(4))[0]
        self.local_position[1] = struct.unpack('<f', file.read(4))[0]
        self.local_position[2] = struct.unpack('<f', file.read(4))[0]
        
        # I don't think the next 42 bytes are important
        file.seek(file.tell() + 42)

    
class Mesh:
    num_submeshes : int
    Vertices = []
    Faces = []

    def __init__(self, file):
    
        # Padding
        file.seek(file.tell() + 8)
        
        # Mesh sub-object allocation
        self.num_submeshes = int.from_bytes(file.read(4), byteorder='little')
        #print("cursor position:", hex(file.tell()))
        
        # Mesh triangle positions
        vertexcount = 4
        facecount = 2
        
        for vert in range(vertexcount):
            x = struct.unpack('<f', file.read(4))[0]
            y = struct.unpack('<f', file.read(4))[0]
            z = struct.unpack('<f', file.read(4))[0]
            self.Vertices.append((x, y, z))
                 
        for vert in range(vertexcount):
            s = struct.unpack('<f', file.read(4))[0]
            t = struct.unpack('<f', file.read(4))[0]
            
        for vert in range(vertexcount):
            norm_x = struct.unpack('<f', file.read(4))[0]
            norm_y = struct.unpack('<f', file.read(4))[0]
            norm_z = struct.unpack('<f', file.read(4))[0]
            
        print("cursor position:", hex(file.tell()))
            
        #print("cursor position:", hex(file.tell()))
        
        #Not sure what these are
        file.seek(file.tell() + 4)      
        
        # I strongly think these are connected vertices. Some of these get made into quads. Eventually I will split them
        # up, but for now, let's build the edge loops
        startpoint = file.tell()
        stridecount = struct.unpack('<H', file.read(2))[0]  
        
        # Used for topology formation
        edgeCounter = 0
        num_edgeLoops = 0
        edgeloops = []
        
        # Let's count all of the edge loops right here
        for s in range(stridecount):
            value = struct.unpack('<H', file.read(2))[0]
            # The value can sometimes vary here, but I will just use a catch all
            if (value > 65500):
                edgeloops.append(edgeCounter)
                edgeCounter = 0
            else:
                edgeCounter += 1
                num_edgeLoops += 1
        
        # Go back to the data block
        file.seek(startpoint)
           
        # Now, for each edge loop, do this:
        for a in range(num_edgeLoops):
            counter = edgeloops[a]
            
            num_quads = counter % 3
            num_tris = (counter - (4 * num_quads)) // 3
            
            subFaces = []
            
            for f in range(num_quads):
                vert1 = struct.unpack('<H', file.read(2))[0]
                vert2 = struct.unpack('<H', file.read(2))[0]
                vert3 = struct.unpack('<H', file.read(2))[0]
                vert4 = struct.unpack('<H', file.read(2))[0]
                subFaces.append((vert1, vert2, vert3, vert4))
            
            for f in range(num_tris):
                vert1 = struct.unpack('<H', file.read(2))[0]
                vert2 = struct.unpack('<H', file.read(2))[0]
                vert3 = struct.unpack('<H', file.read(2))[0]
                subFaces.append((vert1, vert2, vert3))
            
            # Start new connected group
            if edgeCounter > 0:
                file.seek(file.tell() + 2)
                edgeCounter -= 1
        

GHB_MAGIC = 0x198237FE 
GHB_VERSION = 0x033FB1A3
GHB_HEADER_SIZE = 0x4A
            
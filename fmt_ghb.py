from math import pi, sin, cos, atan2, acos
from .utils import AnyStruct
import numpy as np
import struct
import bmesh

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

# GFL's behave a little different from GHL's
AnimatedModel : bool
# Stack of animations
Animations = []
# Where in the raw mesh data the vertex positions begin
VertexPositionStart : int
# Where in the raw mesh data the UVs begin
VertexUVStart : int
# Where in the raw mesh data the normals begin
VertexNormalStart : int
# Seems to have some relation to the amount of edge data but not positive
StrideCountLocation : int
# Edge loops/triangle strips. I have a strong feeling 0xFFFC marks new triangle strips
EdgeLoopStart : int
# Appears to be some kind of lookup table when actually building the vertices
TrueVertexArrayStart: int
# Apparently uses single values? Weird stuff, man
SingleVertexArrayStart: int
# We need to track vertex positions, since not every vertex is in the position array
TotalVertexPositions : int
# This is the number of UV coordinates
TotalVertexUVs : int
# This is the number of normals
TotalVertexNormals : int

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
    identifier : int                # This represents an id of the mesh object
    
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
        
        # I don't think the next 12 bytes are important
        file.seek(file.tell() + 26)
        
        # I believe this is the id of the mesh object
        self.identifier = int.from_bytes(file.read(4), byteorder='little')
        #print("mesh id is:", self.identifier)
        
        # These I doubt to be important
        file.seek(file.tell() + 12)

    
class Mesh:
    num_submeshes : int
    Vertices = []
    Positions = []
    UVs = []
    Normals = []
    Faces = []

    def __init__(self, file, dataoffset, bmeshobj):
        
        # Mesh sub-object allocation
        #self.num_submeshes = int.from_bytes(file.read(4), byteorder='little')
        #print("cursor position:", hex(file.tell()))
        
        # Move to the vertex position array
        file.seek(dataoffset + VertexPositionStart)
        for vert in range(TotalVertexPositions):   
            # Get the position
            x = struct.unpack('<f', file.read(4))[0]
            y = struct.unpack('<f', file.read(4))[0]
            z = struct.unpack('<f', file.read(4))[0]
            pos = (x, y, z)
            self.Positions.append(pos)
            
        # Move to the UV array
        file.seek(dataoffset + VertexUVStart) 
        for vert in range(TotalVertexUVs): 
            # Get the UV Coordinates
            u = struct.unpack('<f', file.read(4))[0]
            v = struct.unpack('<f', file.read(4))[0]
            uv = (u, v)
            self.UVs.append(uv)
        
        # Move to the normals array
        file.seek(dataoffset + VertexNormalStart)        
        for vert in range(TotalVertexNormals): 
            # Get the normal
            norm_x = struct.unpack('<f', file.read(4))[0]
            norm_y = struct.unpack('<f', file.read(4))[0]
            norm_z = struct.unpack('<f', file.read(4))[0]
            normal = (norm_x, norm_y, norm_z)
            self.Normals.append(normal)

        # Move to the normals array
        file.seek(dataoffset + StrideCountLocation)     
        
        # Used for topology formation
        num_edgeLoops = 0
        edgeloops = []        

        file.seek(dataoffset + EdgeLoopStart)

        #Let's count all of the edge loops right here
        edgeBlock = (TrueVertexArrayStart - EdgeLoopStart) // 2
        
        for s in range(edgeBlock):
            # Check for terminator bytes. In some cases these appear and I can tell you they are useless
            terminator = int.from_bytes(file.peek(4)[:4], byteorder='little') == 0
            index = -1
            value = struct.unpack('<H', file.read(2))[0]
            #The value can sometimes vary here, but I will just use a catch all
            if (value == 65532):
                edgeloops.append(0)
                num_edgeLoops += 1
                index += 1
            elif (value == 65535):
                break
            elif (terminator == False):
                edgeloops[index] += 1
            else:
                file.seek(file.tell() + 4)
                
        # This is the true vertex array
        file.seek(dataoffset + TrueVertexArrayStart)  
        for s in range((SingleVertexArrayStart - TrueVertexArrayStart) // 6):
            value = struct.unpack('<h', file.read(2))[0]
            # Get the position of the actual vertex
            if(value < 0):
                index = (abs(value) - 1) % TotalVertexPositions
                final_pos = self.Positions[index]
            else:
                index = value % TotalVertexPositions
                final_pos = self.Positions[index]
                
            value = struct.unpack('<h', file.read(2))[0]
            # Get the UV of the actual vertex
            if(value < 0):
                index = (abs(value) - 1) % TotalVertexUVs
                final_uv = self.UVs[index]
            else:
                index = value % TotalVertexUVs
                final_uv = self.UVs[index]
                
            # Get the normal of the actual vertex
            value = struct.unpack('<h', file.read(2))[0]
            if(value < 0):
                index = (abs(value) - 1) % TotalVertexNormals
                final_norm = self.Normals[index]
            else:
                index = value % TotalVertexNormals
                final_norm = self.Normals[index]
            
            # Now we can finally create the true vertices
            self.Vertices.append(Vertex(final_pos, final_uv, final_norm))
            bmeshobj.verts.new(final_pos) 
        
        # Now we must also do the single's array
#        while(file.peek(1) != b''):
#            value = struct.unpack('B', file.read(1))[0]
#            # Get the position of the actual vertex
#            index = value % TotalVertexPositions
#            final_pos = self.Positions[index]
                
#            value = struct.unpack('B', file.read(1))[0]
            # Get the UV of the actual vertex
#            index = value % TotalVertexUVs
#            final_uv = self.UVs[index]
                
            # Get the normal of the actual vertex
#            value = struct.unpack('B', file.read(1))[0]
#            index = value % TotalVertexNormals
#            final_norm = self.Normals[index]
                
            # Now we can finally create the true vertices
#            self.Vertices.append(Vertex(final_pos, final_uv, final_norm))
#            bmeshobj.verts.new(final_pos) 
         
        bmeshobj.verts.ensure_lookup_table()
               
        # Go back to the start      
        file.seek(dataoffset + EdgeLoopStart)  
        
        # Now, for each edge loop, do this:
        for a in range(num_edgeLoops):
            
            # Start new strip
            if(struct.unpack('<H', file.peek(2)[:2])[0] == 65532):
                file.seek(file.tell() + 2)

            # Draw the triangle strip
            vert1 = struct.unpack('<H', file.read(2))[0]
            vert2 = struct.unpack('<H', file.read(2))[0]

            print("edge loop count is:", edgeloops[a])
            for b in range(2, edgeloops[a]):
                if (b % 2 == 0):
                    print("b value is:", b)
                    vert1 = bmeshobj.verts[b - 1]
                    vert2 = bmeshobj.verts[b - 2]
                    vert3 = bmeshobj.verts[struct.unpack('<H', file.read(2))[0]]
                else:
                    vert1 = bmeshobj.verts[b - 2]
                    vert2 = bmeshobj.verts[b - 1]
                    vert3 = bmeshobj.verts[struct.unpack('<H', file.read(2))[0]]

                # Attach the face
                bmeshobj.faces.new([vert1, vert2, vert3])   
      
        bmeshobj.faces.ensure_lookup_table()
        
class Vertex:
    def __init__(self, vert_pos, vert_uv, vert_normal):
        self.position = vert_pos
        self.uv = vert_uv
        self.normal = vert_normal

GHB_MAGIC = 0x198237FE 
GHB_VERSION = 0x033FB1A3
GHB_HEADER_SIZE = 0x4A
            

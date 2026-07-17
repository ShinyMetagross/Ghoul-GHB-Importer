import bpy
import mathutils
import os.path
import struct

from . import fmt_ghb as fmt

class GHBImporter:
    def __init__(self, context):
        self.context = context
     
    @property
    def scene(self):
        return self.context.scene
    
    def unpack(self, rtype):
        return rtype.funpack(self.file)
     
    def pre_settings(self):
        # Delete these two objects
        if 'Cube' in bpy.data.objects:
            bpy.data.objects['Cube'].select = True

        if 'Lamp' in bpy.data.objects:
            bpy.data.objects['Lamp'].select = True

        # Delete the object
        bpy.ops.object.delete()
     
    def post_settings(self):
        self.scene.frame_set(0)
        self.scene.game_settings.material_mode = 'GLSL'
        bpy.ops.object.lamp_add(type='HEMI')
        
    def __call__(self, filename):
        self.filename = filename
        self.pre_settings()
        with open(filename, 'rb') as file:
            self.file = file

            header = self.unpack(fmt.Header)
            assert header.magic == fmt.GHB_MAGIC
            assert header.version == fmt.GHB_VERSION
            assert header.header_size == fmt.GHB_HEADER_SIZE
            self.headerOffset = 0x1C    
                       
            # Move the cursor to the path offset
            self.file.seek(self.headerOffset)
            
            # Now read the path
            fmt.ghoul_name = self.file.read(header.path_length).decode('utf-8', errors='ignore')
            
            # We must now create the object
            mesh_data = bpy.data.meshes.new(fmt.ghoul_name)
            new_object = bpy.data.objects.new(fmt.ghoul_name, mesh_data)
            current_scene = bpy.context.scene
            current_scene.objects.link(new_object)    
            current_scene.update()

            # Read the extended header
            extHeader = self.unpack(fmt.ExtHeader)
            
            new_object.scale = (extHeader.scale, extHeader.scale, extHeader.scale)
            
            # Unpack animations
            # The offset will be the header, followed by the path, and the size of the extended header
            animationOffset = 0x1C + header.path_length + 24
            self.file.seek(animationOffset)
            
            for x in range(extHeader.anim_count):
                animation = fmt.Animation(self.file)
                fmt.Animations.append(animation)
                
            # These are the tags
            unknown1Collection = fmt.Unknown1Collection(file)
            print("Cursor position at:", hex(file.tell()))
            
            # The next 34 bytes are probably unimportant
            file.read(34)
            
            # This next section is a tree, of sorts

        self.post_settings()
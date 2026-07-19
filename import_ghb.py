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
        
    def generate_Tag_Tree(self, item):
        tag = bpy.data.objects.new(item.bolton_name, None)
        bpy.context.scene.objects.link(tag)
        tag.location = item.global_position
        
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
            
            # Is this animated? This does change some behavior in the bolt-on parser
            fmt.AnimatedModel = fmt.ghoul_name.lower().endswith("gfl")
            
            # We must now create the object
            mesh_data = bpy.data.meshes.new(fmt.ghoul_name)
            new_object = bpy.data.objects.new(fmt.ghoul_name, mesh_data)
            current_scene = bpy.context.scene
            current_scene.objects.link(new_object)    
            current_scene.update()

            # Read the extended header
            extHeader = self.unpack(fmt.ExtHeader)
                        
            # Unpack animations    
            for x in range(extHeader.anim_count):
                # The first animation has useful info, the subsequent runs do not seem so
                self.file.seek(file.tell() + 16)
                      
                animation = fmt.Animation(self.file)
                fmt.Animations.append(animation)
                
            # These are the tags
            unknown1Collection = fmt.Unknown1Collection(file)

            # The next 30 bytes are probably unimportant
            file.seek(file.tell() + 30)
            
            # This next section is the tree of tags
            boltOnTree = fmt.BoltOnTree(self.file, fmt.AnimatedModel)
            for x in range(boltOnTree.num_children):
                self.generate_Tag_Tree(boltOnTree.children[x])

        self.post_settings()
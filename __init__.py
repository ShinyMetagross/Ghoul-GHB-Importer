bl_info = {
    "name": "Ghoul GHB Model (.ghb)",
    "author": "Andrew Clarke, Ned Heller",
    "version": (0, 0, 1),
    "blender": (2, 79, 0),
    "location": "File > Import-Export > Ghoul GHB Model",
    "description": "GHOUL GHB format (.ghb)",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/Import-Export/MD3",
    "tracker_url": "https://github.com/neumond/blender-md3/issues",
    "category": "Import-Export",
}

import bpy
import struct
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper

class ImportGHB(bpy.types.Operator, ImportHelper):
    '''Import a GHOUL GHB file'''
    bl_idname = "import_scene.ghb"
    bl_label = "Import GHOUL Model (.ghb)"
    filename_ext = ".ghb"
    filter_glob = StringProperty(default="*.ghb", options={'HIDDEN'})

    def execute(self, context):
        from .import_ghb import GHBImporter
        GHBImporter(context)(self.properties.filepath)
        return {'FINISHED'}

# Add to the menu
def menu_func_import(self, context):
    self.layout.operator(ImportGHB.bl_idname, text="Ghoul GHB Model (.ghb)")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
   
    
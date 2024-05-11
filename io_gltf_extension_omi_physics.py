# SPDX-FileCopyrightText: © 2024 Marvin Spahn
# SPDX-License-Identifier: MIT

import bpy

bl_info = {
    "name": "glTF Export OMI Physics Extension",
    "description": "Add Rigidbody physics as extension in glTF 2.0 after the OMI specification.",  # noqa
    "author": "Marvin Spahn",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "File > Export > glTF 2.0",
    "doc_url": "https://github.com/marvinspahn/blender-gltf-extensions",
    "category": "Import-Export"
}

extension_is_required = False


class GLTFPhysicsExtensionProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name=bl_info["name"],  # noqa: F821
        description='Include this extension in the exported glTF file',  # noqa: F722, E501
        default=True
    )

    trigger_prop_name: bpy.props.StringProperty(
        name='Trigger Property Name',  # noqa: F722
        description='Change the name of the custom property to determine triggers',  # noqa: F722, E501
        default='omi_trigger'  # noqa: F821
    )


class GLTFPhysicsExtensionAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        props = bpy.context.scene.GLTFPhysicsExtensionProperties
        layout = self.layout
        layout.use_property_split = True
        layout.prop(props, 'trigger_prop_name')


class GLTF_PT_UserExtensionPhysicsPanel(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = ''
    bl_parent_id = 'GLTF_PT_export_user_extensions'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator
        return operator.bl_idname == "EXPORT_SCENE_OT_gltf"

    def draw_header(self, context):
        props = bpy.context.scene.PhysicsExtensionProperties
        self.layout.prop(props, 'enabled')

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation

        props = bpy.context.scene.PhysicsExtensionProperties
        layout.active = props.enabled

        layout.prop(props, "trigger_prop_name", text="Trigger property name")


class glTF2ExportUserExtension:
    """
    Creates additional data in the gltf file for every blender object that
    has a rigidbody. Tries to follow the specification of the Open Metaverse
    Interoperability Group
    https://github.com/omigroup/gltf-extensions/tree/main/extensions/2.0/OMI_physics_body
    https://github.com/omigroup/gltf-extensions/tree/main/extensions/2.0/OMI_physics_shape
    """
    def __init__(self):
        from io_scene_gltf2.io.com.gltf2_io_extensions import Extension
        self.Extension = Extension
        self.props = bpy.context.scene.PhysicsExtensionProperties
        self.collision_shapes = []
        # save unique names in dictionary to reuse meshes with the same shape
        self.mesh_ref_dict = {}
        self.extension_payload = {}

    def gather_gltf_extensions_hook(self, gltf2_plan, export_settings):
        if not self.props.enabled:
            return
        gltf2_plan.extensions["OMI_physics_shape"] = self.Extension(
            name="OMI_physics_shape",
            extension={"shapes": self.collision_shapes},
            required=False
        )

    def gather_node_hook(self, gltf2_node, blender_object, export_settings):
        if not self.props.enabled:
            return

        if not blender_object.rigid_body:
            return

        physics_body_type = "collider"
        mass = 0
        motion_type = ""
        if blender_object.rigid_body.type == 'ACTIVE':
            physics_body_type = "motion"
            mass = blender_object.rigid_body.mass
            motion_type = "dynamic"
            if blender_object.rigid_body.kinematic:
                motion_type = "kinematic"
            if not blender_object.rigid_body.enabled:
                motion_type = "static"
                self.extension_payload = {
                    "type": motion_type,
                    "mass": mass
                }
            gltf2_node.extensions["OMI_physics_body"] = self.Extension(
                name="OMI_physics_body",
                extension={physics_body_type: self.extension_payload},
                required=extension_is_required
            )
            return

        if self.props.trigger_prop_name in blender_object:
            physics_body_type = "trigger"
            if blender_object[self.props.trigger_prop_name] is True:
                self.extension_payload = {
                    "node": []
                }
        shape_index = len(self.collision_shapes)
        should_create_new_shape = True
        if blender_object.data.name not in self.mesh_ref_dict:
            self.mesh_ref_dict[blender_object.data.name] = [
                shape_index,
                blender_object.rigid_body.collision_shape
            ]
        elif (self.mesh_ref_dict[blender_object.data.name][1]
                == blender_object.rigid_body.collision_shape):
            shape_index = self.mesh_ref_dict[blender_object.data.name][0]
            should_create_new_shape = False

        if should_create_new_shape:
            match blender_object.rigid_body.collision_shape:
                case 'BOX':
                    self.collision_shapes.append({
                        "type": "box",
                        "box": {
                            "size": [
                                # convert size to OpenGl coordinate system
                                blender_object.dimensions[0],
                                blender_object.dimensions[2],
                                blender_object.dimensions[1]]
                        }
                    })
                case 'SPHERE':
                    self.collision_shapes.append({
                        "type": "sphere",
                        "sphere": {
                            "radius": max(blender_object.dimensions) / 2
                        }
                    })
                case 'CYLINDER':
                    self.collision_shapes.append({
                        "type": "cylinder",
                        "cylinder": {
                            "height": blender_object.dimensions[2],
                            "radius": max([
                                blender_object.dimensions[0],
                                blender_object.dimensions[1]]) / 2
                        }
                    })
                case 'CAPSULE':
                    self.collision_shapes.append({
                        "type": "capsule",
                        "capsule": {
                            "height": blender_object.dimensions[2],
                            "radius": max([
                                blender_object.dimensions[0],
                                blender_object.dimensions[1]]) / 2
                        }
                    })
                case 'MESH':
                    self.collision_shapes.append({
                        "type": "trimesh",
                        "trimesh": {
                            "mesh": gltf2_node.mesh
                        }
                    })
                case 'CONVEX_HULL':
                    self.collision_shapes.append({
                        "type": "convex",
                        "convex": {
                            "mesh": gltf2_node.mesh
                        }
                    })
                case 'COMPOUND':
                    self.extension_payload = {"shape": {}}

        if not self.extension_payload:
            self.extension_payload = {
                "shape": shape_index
            }

        gltf2_node.extensions["OMI_physics_body"] = self.Extension(
            name="OMI_physics_body",
            extension={physics_body_type: self.extension_payload},
            required=extension_is_required
        )


def register():
    bpy.utils.register_class(GLTFPhysicsExtensionProperties)
    bpy.utils.register_class(GLTFPhysicsExtensionAddonPreferences)
    props = bpy.props.PointerProperty(type=GLTFPhysicsExtensionProperties)
    bpy.types.Scene.GLTFPhysicsExtensionProperties = props


def register_panel():
    try:
        bpy.utils.register_class(GLTF_PT_UserExtensionPhysicsPanel)
    except Exception:
        pass
    return unregister_panel


def unregister_panel():
    try:
        bpy.utils.unregister_class(GLTF_PT_UserExtensionPhysicsPanel)
    except Exception:
        pass


def unregister():
    unregister_panel()
    bpy.utils.unregister_class(GLTFPhysicsExtensionProperties)
    bpy.utils.unregister_class(GLTFPhysicsExtensionAddonPreferences)
    del bpy.types.Scene.PhysicsExtensionProperties

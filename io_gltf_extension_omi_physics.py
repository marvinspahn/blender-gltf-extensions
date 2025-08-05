# SPDX-FileCopyrightText: © 2024 Marvin Spahn
# SPDX-License-Identifier: MIT

import bpy


bl_info = {
    "name": "glTF Export OMI Physics Extension",
    "description": "Add Rigidbody physics as extension in glTF 2.0 after the OMI specification.",  # noqa
    "author": "Marvin Spahn",
    "version": (1, 3),
    "blender": (4, 4, 0),
    "location": "File > Export > glTF 2.0",
    "doc_url": "https://github.com/marvinspahn/blender-gltf-extensions",
    "category": "Import-Export"
}


glTF_extension_name = "EXT_omi_physics"
extension_is_required = False


class GLTFPhysicsExtensionProperties(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(
        name=bl_info["name"],  # noqa: F722, F821
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
        layout.prop(props, 'use_collider_method')
        layout.prop(props, 'trigger_prop_name')


# TODO make rigidbody setup easier with setup operators
class GLTF_OT_OMIRigidbodySetupOperator(bpy.types.Operator):
    bl_label = "OMI Physics Setup Rigidbody"
    bl_idname = "omi_physics.setup_rigidbody"

    def execute(self, context):
        return {'FINISHED'}


class GLTF_OT_OMITriggerPropertyOperator(bpy.types.Operator):
    """Creates a custom trigger property on the current object."""
    bl_label = "OMI Physics Toggle Trigger Property"
    bl_idname = "omi_physics.toggle_trigger_prop"
    bl_description = "Toggle to convert the rigidbody to a trigger volume during export"  # noqa

    def execute(self, context):
        props = context.scene.GLTFPhysicsExtensionProperties
        obj = context.object
        if props.trigger_prop_name in obj:
            del obj[props.trigger_prop_name]
        else:
            obj[props.trigger_prop_name] = True
        return {'FINISHED'}


class GLTF_PT_OMIPhysicsPanel(bpy.types.Panel):
    """
    Creates a panel in the physics properties
    window for additional settings and setups.
    """
    bl_label = "OMI Physics"
    bl_idname = "PHYSICS_PT_OMIPhysics"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "physics"

    @classmethod
    def poll(cls, context):
        return context.object.rigid_body

    def draw(self, context):
        layout = self.layout
        obj = context.object
        props = context.scene.GLTFPhysicsExtensionProperties
        row = layout.row()
        if props.trigger_prop_name not in obj:
            row.operator("omi_physics.toggle_trigger_prop",
                         text="Trigger Disabled",
                         icon='HIDE_ON')
        else:
            row.operator("omi_physics.toggle_trigger_prop",
                         text="Trigger Enabled",
                         icon='HIDE_OFF')


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
        self.props = bpy.context.scene.GLTFPhysicsExtensionProperties
        self.collision_shapes = []
        # save unique names in dictionary to reuse meshes with the same shape
        self.mesh_ref_dict = {}

    def create_physics_bodies(self, gltf2_node, blender_object):
        # init variables
        extension_payload = {}
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
            extension_payload = {
                "type": motion_type,
                "mass": mass
            }
            gltf2_node.extensions["OMI_physics_body"] = self.Extension(
                name="OMI_physics_body",
                extension={physics_body_type: extension_payload},
                required=extension_is_required
            )
            return

        if self.props.trigger_prop_name in blender_object:
            physics_body_type = "trigger"
        shape_index = len(self.collision_shapes)
        should_create_new_shape = True
        shape = blender_object.rigid_body.collision_shape
        data_name = blender_object.data.name
        if data_name not in self.mesh_ref_dict:
            self.mesh_ref_dict[data_name] = {
                shape: shape_index
            }
        elif shape in self.mesh_ref_dict[data_name]:
            shape_index = self.mesh_ref_dict[data_name][shape]
            should_create_new_shape = False
        else:
            self.mesh_ref_dict[data_name][shape] = shape_index

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
                    extension_payload = {"shape": {}}
        if not extension_payload:
            extension_payload = {
                "shape": shape_index
            }

        gltf2_node.extensions["OMI_physics_body"] = self.Extension(
            name="OMI_physics_body",
            extension={physics_body_type: extension_payload},
            required=extension_is_required
        )

    def gather_gltf_extensions_hook(self, gltf2_plan, export_settings):
        if not self.props.enabled:
            return
        if not len(self.collision_shapes):
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

        self.create_physics_bodies(gltf2_node, blender_object)


def register():
    bpy.utils.register_class(GLTFPhysicsExtensionProperties)
    bpy.utils.register_class(GLTFPhysicsExtensionAddonPreferences)
    bpy.utils.register_class(GLTF_OT_OMIRigidbodySetupOperator)
    bpy.utils.register_class(GLTF_OT_OMITriggerPropertyOperator)
    bpy.utils.register_class(GLTF_PT_OMIPhysicsPanel)
    props = bpy.props.PointerProperty(type=GLTFPhysicsExtensionProperties)
    bpy.types.Scene.GLTFPhysicsExtensionProperties = props


def unregister():
    bpy.utils.unregister_class(GLTFPhysicsExtensionProperties)
    bpy.utils.unregister_class(GLTFPhysicsExtensionAddonPreferences)
    bpy.utils.unregister_class(GLTF_OT_OMIRigidbodySetupOperator)
    bpy.utils.unregister_class(GLTF_OT_OMITriggerPropertyOperator)
    bpy.utils.unregister_class(GLTF_PT_OMIPhysicsPanel)
    del bpy.types.Scene.GLTFPhysicsExtensionProperties


def draw_export(context, layout):
    header, body = layout.panel("GLTF_addon_example_exporter",
                                default_closed=False)
    header.use_property_split = False

    props = bpy.context.scene.GLTFPhysicsExtensionProperties

    header.prop(props, 'enabled')
    if body is not None:
        body.prop(props, 'float_property', text="Some float value")
    # row = layout.row()
    # row.use_property_split = False
    # props = bpy.context.scene.GLTFPhysicsExtensionProperties
    # row.prop(props, "enabled")

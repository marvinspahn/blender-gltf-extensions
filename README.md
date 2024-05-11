# blender-gltf-extensions
Addons for Blender utilizing glTF 2.0 user extensions.
## OMI Physics Export (io_gltf_extension_omi_physics.py)
This addon adds support for the OMI_physics_body and OMI_physics_shape extension to Blender. The specification can be found [here](https://github.com/omigroup/gltf-extensions/tree/main/extensions/2.0/OMI_physics_body). I made it to export gltf files to Godot, which supports this extension and enables you to do basic collision setups directly in Blender.
### Setup
The addon makes use of the Blender specific rigidbody system in the Physics tab of the Properties Panel. When an object has a rigidbody it will be seen during export and the extension will be added to the node in the gltf file. The following settings are supported in the extension:

| Blender  | GLTF | Godot 4.0 |
| ------------- | ------------- | ------------- | 
| Type | Active → Dynamic, Passive → Static | Active → RigidBody3D, Passive → StaticBody3D |
| Mass (Active Only)  | mass | mass |
| Dynamic (Active Only) | ☑ Dynamic ☐ Static | (Type is Active) → ☑ RigidBody3D ☐ StaticBody3D |
| Animated (Active Only) | ☑ Kinematic | ☑ AnimatableBody3D ☐ RigidBody3D |
| Shape | Box, Sphere, Capsule, Cylinder, Convex Hull, Mesh | same |


#### Compound Shapes
The extension supports compound shapes which are multiple shapes under one physics body. Select `Compound Parent` for the rigidbody collision shape and parent multiple other **passive** rigidbody objects under the physics body.
> [!NOTE]
> Even though blender hides certain settings when using compound shapes (eg. when parenting a compound parent shape rigidbody to another one) they are still being read by the addon and necessary to be set before parenting child rigidbodies to the compound parent.
#### Instanced Shapes
When linking object data `(CTRL + L → Link Object Data)` in Blender the addon will try and reference only one shape for all users that use that shape. Rigidbodies need the same mesh and shape property for it to work.
#### Triggers
Since Blender does not know of the concept of triggers a custom property needs to be added to the object so that it is to be recognized as a trigger/triggershape. The default is a boolean property named `omi_trigger`. If it is True the object will act as the trigger body. If False it will be a trigger shape when parented under a trigger body with `Compound Parent` as Collision Shape. Otherwise it will also be a trigger body with an automatic shape derived from the rigidbody.
The trigger property name can be changed in the addon preferences.

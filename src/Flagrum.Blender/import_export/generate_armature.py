import bpy
from mathutils import Matrix, Vector
from numpy.linalg import solve

from ..utilities.bpy_context import set_object_mode
from .import_context import ImportContext

# NOTE: The legacy ``createEmptyTree`` / ``createRootNub`` / ``createNub`` /
# ``_generate_armature`` helpers were removed during the Blender 5
# modernisation. They depended on APIs (``scene.objects.link``,
# ``scene.update``, ``Object.show_x_ray``, ``Object.empty_draw_size``) that
# no longer exist, and nothing referenced them outside of each other.


def visitBones(bone, visited):
    visited.add(bone.id)
    for child in bone.children:
        if child.id in visited:
            raise ValueError(f"Cycle Detected at bone {bone.id}:{bone.name}")
        visitBones(child, visited)
    return visited


def detectCycles(root, miniscene):
    for rootb in root:
        visited = set()
        visitBones(rootb, visited)
    for bid in miniscene:
        if bid not in visited:
            bone = miniscene[bid]
            raise ValueError(f"Disconnected Bone {bone.id}:{bone.name}")
    return


def processArmatureData(armature_data):
    root = []
    miniscene = {}
    for bone in armature_data.bones:
        if bone.id in miniscene:
            raise KeyError(f"Duplicated ID {bone.id}")
        else:
            bone.children = []
            miniscene[bone.id] = bone
            bone.matrix = Matrix(solve(bone.transformation_matrix, Matrix.Identity(4)))
    for bone in armature_data.bones:
        if bone.id:
            bone.parent = miniscene[armature_data.parent_IDs[bone.id - 1]]
            miniscene[armature_data.parent_IDs[bone.id - 1]].children.append(bone)
        else:
            root.append(bone)
            bone.parent = None
    detectCycles(root, miniscene)
    return root


def distance(point, origin, line):
    pointPrime = point - origin
    a = pointPrime.project(line).magnitude
    c = pointPrime.magnitude
    return c ** 2 - a ** 2


def minimizeDistance(origin, transform, points):
    line = transform @ Vector([0, 1, 0])
    minima = -1
    minimizer = None
    dst = None
    for point in points:
        if point.matrix.translation == origin:
            continue
        d = distance(point.matrix.translation, origin, line)
        if 0 < d < minima or minima == -1:
            minima = d
            minimizer = point
            dst = (point.matrix.translation - origin).magnitude
            break
    if minimizer is None:
        return None
    return origin + (transform @ Vector([0, dst, 0, 0])).to_3d()


def matGen(ixlist):
    m = [[1 if j == i else (-1 if j == i % 10 else 0) for j in range(len(ixlist))] for i in ixlist]
    return Matrix(m)


def createBone(bone, armature, parent=None, per=(1, 2, 0, 3)):
    new_bone = armature.edit_bones.new(bone.name)
    new_bone["ID"] = bone.id
    transformedMatrix = bone.matrix
    if parent:
        new_bone.parent = parent
        correction = matGen(per)
        transform = transformedMatrix @ correction
    else:
        correction = matGen(per)
        transform = transformedMatrix @ correction
    new_bone.head = transform.translation
    preferred = minimizeDistance(transform.translation, transform, bone.children)
    if preferred is None:
        if parent is not None:
            delta = transform @ Vector([0, min(0.01, parent.length), 0, 0])
            preferred = transform.translation + delta.to_3d()
        else:
            preferred = transform.translation + transform @ Vector([0, 0.01, 0])
    if preferred == transform.translation:
        preferred = transform.translation + Vector([0, 0.01, 0])
    new_bone.tail = preferred
    new_bone.matrix = transform
    if new_bone.length < 0.0001:
        new_bone.tail = new_bone.head + Vector([0, 0.01, 0])
    for child in bone.children:
        createBone(child, armature, new_bone, per)


def generate_armature(context: ImportContext, armature_data):
    armature_name = context.collection.name
    armature = bpy.data.armatures.new(armature_name)
    armature_object = bpy.data.objects.new(armature_name, armature)
    armature_object.data.name = armature_name
    armature.display_type = "STICK"
    context.root_collections.link_to_scene()
    context.collection.objects.link(armature_object)
    bpy.context.view_layer.objects.active = armature_object
    set_object_mode(armature_object, "EDIT")

    root = processArmatureData(armature_data)
    for rootb in root:
        createBone(rootb, armature)
    set_object_mode(armature_object, "OBJECT")

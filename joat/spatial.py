import math

from panda3d.core import LMatrix3, LMatrix4, LQuaternion, LVecBase3, TransformState


def make_rotation(angle: float, axis: LVecBase3) -> LQuaternion:
    """Return a quaternion representing a rotation
    with the given characteristics.
    """
    half_angle = angle / 2
    cosine = math.cos(half_angle)
    sine = math.sin(half_angle)
    return LQuaternion(cosine, axis.normalized() * sine)


def required_rotation(u: LVecBase3, v: LVecBase3, /) -> LQuaternion:
    """Return a quaternion representing the rotation
    required to align `u` with `v`.
    """
    u, v = u.normalized(), v.normalized()
    axis = u.cross(v)
    dot_product = u.dot(v)
    cosine = math.sqrt((1 + dot_product) / 2)
    sine = math.sqrt((1 - dot_product) / 2)
    return LQuaternion(cosine, axis * sine)


def make_rigid_transform(
    rotation: LMatrix3 | LQuaternion, translation: LVecBase3
) -> TransformState:
    """Return a TransformState comprising the given rotation
    followed by the given translation.
    """
    if isinstance(rotation, LQuaternion):
        # There isn't a `TransformState.make_pos_quat` constructor.
        return TransformState.make_pos_quat_scale(translation, rotation, LVecBase3(1))
    else:
        return TransformState.make_mat(LMatrix4(rotation, translation))

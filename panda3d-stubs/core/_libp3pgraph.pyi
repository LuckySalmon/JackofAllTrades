from typing import TypeVar, Generic, TypeAlias
from panda3d.core import (
    DrawMask,
    LVecBase3f,
    LVector3f,
    LPoint3f,
    LMatrix3f,
    LMatrix4f,
    UnalignedLMatrix4f,
    Namable,
    NodeCachedReferenceCount,
    PandaNode,
    Thread,
    TypedWritableReferenceCount,
)

_Vec3f: TypeAlias = LVecBase3f | LMatrix3f.Row | LMatrix3f.CRow
_Mat4f: TypeAlias = LMatrix4f | UnalignedLMatrix4f

_T = TypeVar('_T', bound=PandaNode)
_S = TypeVar('_S', bound=PandaNode)

class TransformState(NodeCachedReferenceCount):
    @staticmethod
    def make_pos_hpr(pos: _Vec3f, hpr: _Vec3f) -> TransformState: ...
    @staticmethod
    def make_mat(mat: _Mat4f) -> TransformState: ...
    def get_pos(self) -> LPoint3f: ...
    def get_mat(self) -> LMatrix4f: ...
    makePosHpr = make_pos_hpr
    makeMat = make_mat
    getPos = get_pos
    getMat = get_mat

class PandaNode(TypedWritableReferenceCount, Namable):
    def set_transform(self, transform: TransformState, current_thread: Thread = ...): ...
    setTransform = set_transform

class NodePath(Generic[_T]):
    def node(self) -> _T: ...
    def reparent_to(self, other: NodePath, sort: int = 0, current_thread: Thread = ...) -> None: ...
    def attach_new_node(self, node: _S, sort: int = 0, current_thread: Thread = ...) -> NodePath[_S]: ...
    def get_net_transform(self, current_thread: Thread = ...) -> TransformState: ...
    def set_pos(self, x: float, y: float, z: float) -> None: ...
    def get_pos(self, other: NodePath = ...) -> LPoint3f: ...
    def get_mat(self, other: NodePath = ...) -> LMatrix4f: ...
    def look_at(self, x: float, y: float, z: float) -> None: ...
    def get_relative_point(self, other: NodePath, point: _Vec3f) -> LPoint3f: ...
    def get_relative_vector(self, other: NodePath, vec: _Vec3f) -> LVector3f: ...
    def show(self) -> None: ...
    def hide(self) -> None: ...
    def is_hidden(self, camera_mask: DrawMask = ...) -> bool: ...
    reparentTo = reparent_to
    attachNewNode = attach_new_node
    getNetTransform = get_net_transform
    setPos = set_pos
    getPos = get_pos
    getMat = get_mat
    lookAt = look_at
    getRelativePoint = get_relative_point
    getRelativeVector = get_relative_vector
    isHidden = is_hidden

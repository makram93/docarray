from typing import TYPE_CHECKING, Any, Type, TypeVar, Union, cast

import numpy as np

from docarray.typing.tensor.video.video_ndarray import VideoNdArray
from docarray.typing.tensor.video.video_tensor_mixin import VideoTensorMixin
from docarray.utils._internal.misc import is_tf_available, is_torch_available

torch_available = is_torch_available()
if torch_available:
    import torch

    from docarray.typing.tensor.torch_tensor import TorchTensor  # noqa: F401
    from docarray.typing.tensor.video.video_torch_tensor import VideoTorchTensor


tf_available = is_tf_available()
if tf_available:
    import tensorflow as tf  # type: ignore

    from docarray.typing.tensor.tensorflow_tensor import TensorFlowTensor  # noqa: F401
    from docarray.typing.tensor.video.video_tensorflow_tensor import (
        VideoTensorFlowTensor,
    )

if TYPE_CHECKING:
    from pydantic import BaseConfig
    from pydantic.fields import ModelField

T = TypeVar("T", bound="VideoTensor")


class VideoTensor(VideoTensorMixin):
    """
    Represents a Video tensor object that can be used with TensorFlow, PyTorch, and NumPy type.

    ---

    '''python
    from docarray import BaseDoc
    from docarray.typing import VideoTensor


    class MyVideoDoc(BaseDoc):
        video: VideoTensor


    # Example usage with TensorFlow:
    import tensorflow as tf

    doc = MyVideoDoc(video=tf.zeros(1000, 2))

    # Example usage with PyTorch:
    import torch

    doc = MyVideoDoc(video=torch.zeros(1000, 2))

    # Example usage with NumPy:
    import numpy as np

    doc = MyVideoDoc(video=np.zeros((1000, 2)))
    '''

    Returns:
        Union[VideoTorchTensor, VideoTensorFlowTensor, VideoNdArray]: The validated and converted audio tensor.

    Raises:
        TypeError: If the input value is not a compatible type (torch.Tensor, tensorflow.Tensor, numpy.ndarray).

    """

    def __getitem__(self: T, item):
        pass

    def __setitem__(self, index, value):
        pass

    def __iter__(self):
        pass

    def __len__(self):
        pass

    @classmethod
    def _docarray_from_native(cls: Type[T], value: Any):
        raise AttributeError('This method should not be called on VideoTensor.')

    @staticmethod
    def get_comp_backend():
        raise AttributeError('This method should not be called on VideoTensor.')

    def to_protobuf(self):
        raise AttributeError('This method should not be called on VideoTensor.')

    def _docarray_to_json_compatible(self):
        raise AttributeError('This method should not be called on VideoTensor.')

    @classmethod
    def from_protobuf(cls: Type[T], pb_msg: T):
        raise AttributeError('This method should not be called on VideoTensor.')

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(
        cls: Type[T],
        value: Union[T, np.ndarray, Any],
        field: "ModelField",
        config: "BaseConfig",
    ):
        # Check for TorchTensor first, then TensorFlowTensor, then NdArray
        if torch_available:
            if isinstance(value, TorchTensor):
                return cast(VideoTorchTensor, value)
            elif isinstance(value, torch.Tensor):
                return VideoTorchTensor._docarray_from_native(value)  # noqa
        if tf_available:
            if isinstance(value, TensorFlowTensor):
                return cast(VideoTensorFlowTensor, value)
            elif isinstance(value, tf.Tensor):
                return VideoTensorFlowTensor._docarray_from_native(value)  # noqa
        if isinstance(value, VideoNdArray):
            return cast(VideoNdArray, value)
        if isinstance(value, np.ndarray):
            try:
                return VideoNdArray.validate(value, field, config)
            except Exception as e:  # noqa
                raise e
        raise TypeError(
            f"Expected one of [torch.Tensor, tensorflow.Tensor, numpy.ndarray] "
            f"compatible type, got {type(value)}"
        )

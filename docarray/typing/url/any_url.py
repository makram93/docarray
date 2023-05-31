import mimetypes
import os
import urllib
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING, Any, List, Optional, Type, TypeVar, Union

import numpy as np
from pydantic import AnyUrl as BaseAnyUrl
from pydantic import errors, parse_obj_as

from docarray.typing.abstract_type import AbstractType
from docarray.typing.proto_register import _register_proto

if TYPE_CHECKING:
    from pydantic import BaseConfig
    from pydantic.fields import ModelField
    from pydantic.networks import Parts

    from docarray.proto import NodeProto

T = TypeVar('T', bound='AnyUrl')


@_register_proto(proto_type_name='any_url')
class AnyUrl(BaseAnyUrl, AbstractType):
    host_required = (
        False  # turn off host requirement to allow passing of local paths as URL
    )

    @classmethod
    def mime_type(cls) -> str:
        raise NotImplementedError

    @classmethod
    def allowed_extensions(cls) -> List[str]:
        raise NotImplementedError

    def _to_node_protobuf(self) -> 'NodeProto':
        """Convert Document into a NodeProto protobuf message. This function should
        be called when the Document is nested into another Document that need to
        be converted into a protobuf

        :return: the nested item protobuf message
        """
        from docarray.proto import NodeProto

        return NodeProto(text=str(self), type=self._proto_type_name)

    @classmethod
    def validate(
        cls: Type[T],
        value: Union[T, np.ndarray, Any],
        field: 'ModelField',
        config: 'BaseConfig',
    ) -> T:
        import os

        abs_path: Union[T, np.ndarray, Any]
        if (
            isinstance(value, str)
            and not value.startswith('http')
            and not os.path.isabs(value)
        ):
            input_is_relative_path = True
            abs_path = os.path.abspath(value)
        else:
            input_is_relative_path = False
            abs_path = value

        url = super().validate(abs_path, field, config)  # basic url validation

        # Use mimetypes to validate file formats
        mimetype, encoding = mimetypes.guess_type(value.split("?")[0])
        if not mimetype:
            # try reading from the request headers if mimetypes failed - could be slow
            try:
                r = urllib.request.urlopen(value)
            except Exception:  # noqa
                pass  # should we raise an error/warning here, since url is not reachable(invalid)?
            else:
                mimetype = r.headers.get_content_maintype()

        skip_check = False
        if not mimetype:  # not able to automatically detect mimetype
            # check if the file extension is among one of the allowed extensions
            if not any(
                value.endswith(ext) or value.split("?")[0].endswith(ext)
                for ext in cls.allowed_extensions()
            ):
                raise ValueError(
                    f'file {value} is not a valid file format for class {cls}'
                )
            else:
                skip_check = True  # one of the allowed extensions, skip the check

        if not skip_check and not mimetype.startswith(cls.mime_type()):
            raise ValueError(f'file {value} is not a {cls.mime_type()} file format')

        if input_is_relative_path:
            return cls(str(value), scheme=None)
        else:
            return cls(str(url), scheme=None)

    @classmethod
    def validate_parts(cls, parts: 'Parts', validate_port: bool = True) -> 'Parts':
        """
        A method used to validate parts of a URL.
        Our URLs should be able to function both in local and remote settings.
        Therefore, we allow missing `scheme`, making it possible to pass a file
        path without prefix.
        If `scheme` is missing, we assume it is a local file path.
        """
        scheme = parts['scheme']
        if scheme is None:
            # allow missing scheme, unlike pydantic
            pass

        elif cls.allowed_schemes and scheme.lower() not in cls.allowed_schemes:
            raise errors.UrlSchemePermittedError(set(cls.allowed_schemes))

        if validate_port:
            cls._validate_port(parts['port'])

        user = parts['user']
        if cls.user_required and user is None:
            raise errors.UrlUserInfoError()

        return parts

    @classmethod
    def build(
        cls,
        *,
        scheme: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        host: str,
        port: Optional[str] = None,
        path: Optional[str] = None,
        query: Optional[str] = None,
        fragment: Optional[str] = None,
        **_kwargs: str,
    ) -> str:
        """
        Build a URL from its parts.
        The only difference from the pydantic implementation is that we allow
        missing `scheme`, making it possible to pass a file path without prefix.
        """

        # allow missing scheme, unlike pydantic
        scheme_ = scheme if scheme is not None else ''
        url = super().build(
            scheme=scheme_,
            user=user,
            password=password,
            host=host,
            port=port,
            path=path,
            query=query,
            fragment=fragment,
            **_kwargs,
        )
        if scheme is None and url.startswith('://'):
            # remove the `://` prefix, since scheme is missing
            url = url[3:]
        return url

    @classmethod
    def from_protobuf(cls: Type[T], pb_msg: 'str') -> T:
        """
        Read url from a proto msg.
        :param pb_msg:
        :return: url
        """
        return parse_obj_as(cls, pb_msg)

    def load_bytes(self, timeout: Optional[float] = None) -> bytes:
        """Convert url to bytes. This will either load or download the file and save
        it into a bytes object.
        :param timeout: timeout for urlopen. Only relevant if URI is not local
        :return: bytes.
        """
        if urllib.parse.urlparse(self).scheme in {'http', 'https', 'data'}:
            req = urllib.request.Request(self, headers={'User-Agent': 'Mozilla/5.0'})
            urlopen_kwargs = {'timeout': timeout} if timeout is not None else {}
            with urllib.request.urlopen(req, **urlopen_kwargs) as fp:  # type: ignore
                return fp.read()
        elif os.path.exists(self):
            with open(self, 'rb') as fp:
                return fp.read()
        else:
            raise FileNotFoundError(f'`{self}` is not a URL or a valid local path')

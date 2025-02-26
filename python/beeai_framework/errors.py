# Copyright 2025 IBM Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from asyncio import CancelledError
from collections.abc import Generator


def _format_error_message(e: BaseException, *, offset: int = 0, strip_traceback: bool = True) -> str:
    cls = type(e).__name__
    module = type(e).__module__

    prefix = "  " * offset
    formatted = f"{cls}({module}): {e!s}"
    if strip_traceback:
        formatted = formatted.split("\nTraceback")[0]

    return "\n".join([f"{prefix}{line}" for line in formatted.split("\n")])


class FrameworkError(Exception):
    """
    Base class for Framework errors which extends Exception
    All errors should extend from this base class.
    """

    def __init__(
        self,
        message: str = "Framework error",
        *,
        is_fatal: bool = True,
        is_retryable: bool = False,
        cause: Exception | None = None,  # remove
        predecessor: Exception | None = None,
    ) -> None:
        super().__init__(message)

        # TODO: What other attributes should all our framework errors have?
        self.message = message
        self._is_fatal = is_fatal
        self._is_retryable = is_retryable
        self._predecessor = predecessor or cause

    @property
    def predecessor(self) -> BaseException | None:
        return self._predecessor or self.__cause__

    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """is error retryable?."""
        if isinstance(error, FrameworkError):
            return error.is_retryable
        return not isinstance(error, CancelledError)

    @staticmethod
    def is_fatal(error: Exception) -> bool:
        """is error fatal?"""
        if isinstance(error, FrameworkError):
            return error.is_fatal
        else:
            return False

    def name(self) -> str:
        """get name (class) of this error"""
        return type(self).__name__

    def has_fatal_error(self) -> bool:
        current_exception: BaseException | None = self

        while current_exception is not None:
            if isinstance(current_exception, FrameworkError) and current_exception.is_fatal:
                return True

            current_exception = current_exception.__cause__

        return False

    def traverse(self) -> Generator["FrameworkError", None, None]:
        next: FrameworkError | BaseException | None = self
        while isinstance(next, FrameworkError):
            yield next
            next = next.predecessor

    def get_cause(self) -> BaseException:
        deepest_cause: BaseException = self

        while deepest_cause.__cause__ is not None:
            deepest_cause = deepest_cause.__cause__

        return deepest_cause

    def explain(self) -> str:
        output = []

        for offset, error in enumerate(self.traverse()):
            message = _format_error_message(error, offset=offset)
            output.append(message)

        if error and error.predecessor:
            message = _format_error_message(error.predecessor, offset=offset + 1, strip_traceback=False)
            output.append(message)

        return "\n".join(output)

    @classmethod
    def ensure(cls, error: Exception) -> "FrameworkError":
        if isinstance(error, FrameworkError):
            return error
        return cls(message="Something went wrong!", cause=error)


class UnimplementedError(FrameworkError):
    """
    Raised when a method or function has not been implemented.
    """

    def __init__(self, message: str = "Not implemented!", *, cause: Exception | None = None) -> None:
        super().__init__(message, is_fatal=True, is_retryable=False, predecessor=cause)


class ArgumentError(FrameworkError):
    """Raised for invalid or unsupported values."""

    def __init__(self, message: str = "Provided value is not supported!", *, cause: Exception | None = None) -> None:
        # TODO is a value error fatal. It is with same value...
        super().__init__(message, is_fatal=True, is_retryable=False, predecessor=cause)


class AbortError(FrameworkError, CancelledError):
    """Raised when an operation has been aborted."""

    def __init__(self, message: str = "Operation has been aborted!") -> None:
        super().__init__(message, is_fatal=True, is_retryable=False)

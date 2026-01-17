"""
Base Specification classes.

Provides the foundation for the Specification pattern with
composable boolean operations (AND, OR, NOT).
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Specification(ABC, Generic[T]):
    """
    Base specification class.

    A specification encapsulates a business rule that can be evaluated
    against an entity to determine if it satisfies the rule.

    Specifications can be combined using boolean operations:
    - and_(): Both specifications must be satisfied
    - or_(): At least one specification must be satisfied
    - not_(): The specification must not be satisfied

    Example:
        active_spec = IsActiveSpecification()
        admin_spec = HasRoleSpecification(UserRole.ADMIN)

        # Combine specifications
        active_admin = active_spec.and_(admin_spec)

        # Check if entity satisfies specification
        if active_admin.is_satisfied_by(user):
            print("User is an active admin")
    """

    @abstractmethod
    def is_satisfied_by(self, entity: T) -> bool:
        """
        Check if the entity satisfies this specification.

        Args:
            entity: The entity to check

        Returns:
            True if the entity satisfies the specification, False otherwise
        """
        pass

    def and_(self, other: "Specification[T]") -> "AndSpecification[T]":
        """
        Create a new specification that requires both this and the other
        specification to be satisfied.

        Args:
            other: The other specification

        Returns:
            A new AndSpecification
        """
        return AndSpecification(self, other)

    def or_(self, other: "Specification[T]") -> "OrSpecification[T]":
        """
        Create a new specification that requires at least one of this
        or the other specification to be satisfied.

        Args:
            other: The other specification

        Returns:
            A new OrSpecification
        """
        return OrSpecification(self, other)

    def not_(self) -> "NotSpecification[T]":
        """
        Create a new specification that requires this specification
        to not be satisfied.

        Returns:
            A new NotSpecification
        """
        return NotSpecification(self)

    # Operator overloads for more Pythonic syntax
    def __and__(self, other: "Specification[T]") -> "AndSpecification[T]":
        return self.and_(other)

    def __or__(self, other: "Specification[T]") -> "OrSpecification[T]":
        return self.or_(other)

    def __invert__(self) -> "NotSpecification[T]":
        return self.not_()


class AndSpecification(Specification[T]):
    """
    Composite specification that requires both specifications to be satisfied.
    """

    def __init__(self, left: Specification[T], right: Specification[T]):
        self._left = left
        self._right = right

    def is_satisfied_by(self, entity: T) -> bool:
        return (
            self._left.is_satisfied_by(entity) and
            self._right.is_satisfied_by(entity)
        )

    @property
    def left(self) -> Specification[T]:
        return self._left

    @property
    def right(self) -> Specification[T]:
        return self._right


class OrSpecification(Specification[T]):
    """
    Composite specification that requires at least one specification
    to be satisfied.
    """

    def __init__(self, left: Specification[T], right: Specification[T]):
        self._left = left
        self._right = right

    def is_satisfied_by(self, entity: T) -> bool:
        return (
            self._left.is_satisfied_by(entity) or
            self._right.is_satisfied_by(entity)
        )

    @property
    def left(self) -> Specification[T]:
        return self._left

    @property
    def right(self) -> Specification[T]:
        return self._right


class NotSpecification(Specification[T]):
    """
    Specification that negates another specification.
    """

    def __init__(self, spec: Specification[T]):
        self._spec = spec

    def is_satisfied_by(self, entity: T) -> bool:
        return not self._spec.is_satisfied_by(entity)

    @property
    def specification(self) -> Specification[T]:
        return self._spec

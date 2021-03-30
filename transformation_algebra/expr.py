"""
Classes to define generic transformation algebras.
"""

from __future__ import annotations

from abc import ABC
import pyparsing as pp
from functools import reduce
from typing import Optional, Any, Dict, Callable, Union

from transformation_algebra import error
from transformation_algebra.type import Type, Schema


def typed(
        τ: Union[Type, Callable[..., Type]]) -> Callable[..., Definition]:
    """
    A decorator for defining transformations in terms of other transformations.
    Despite appearances, the provided function is *not* an implementation of
    the transformation: it merely represents a decomposition into more
    primitive conceptual building blocks.
    """
    τ2: Type = τ if isinstance(τ, Type) else Schema(τ)

    def wrapper(func: Callable[..., Expr]) -> Definition:
        return Definition(
            name=func.__name__,
            type=τ2,
            description=func.__doc__,
            composition=func
        )
    return wrapper


class Expr(ABC):
    def __init__(self):
        self.type = None

    def __repr__(self) -> str:
        return str(self)


class Input(Expr):
    """
    Represents input data for a transformation algebra expression. This can
    also be seen as a *typed variable* in an expression.
    """

    def __init__(self, definition: Definition, ident: Optional[str] = None):
        self.definition = definition
        self.type = definition.type.instance()
        self.identifier = ident

        if self.type.is_function():
            raise RuntimeError("Must not be a function type")
        if any(self.type.plain().variables()):
            raise RuntimeError("Input types must be fully qualified")

    def __str__(self) -> str:
        if self.identifier:
            return f"{self.definition.name} {self.identifier} : {self.type}"
        return self.definition.name


class Transformation(Expr):
    def __init__(self, definition: Definition):
        self.definition = definition
        self.type = definition.type.instance()

        if not self.type.is_function():
            raise RuntimeError("Must be a function type")

    def __str__(self) -> str:
        return self.definition.name


class Result(Expr):
    """
    Represents an *application* of a transformation.
    """

    def __init__(self, f: Expr, x: Expr):
        self.f = f
        self.x = x
        try:
            self.type = f.type.instance().apply(x.type.instance())
        except error.AlgebraTypeError as e:
            e.add_expression(f, x)
            raise e

    def __str__(self) -> str:
        return f"({self.f} {self.x} : {self.type})"


class Definition(object):
    """
    A definition represents a non-instantiated data input or transformation.
    """

    def __init__(
            self,
            name: str,
            type: Type,
            named: bool = False,
            description: Optional[str] = None,
            composition: Optional[Callable[..., Expr]] = None):
        self.name = name
        self.type = type
        self.named = named  # are instances identified or anonymous?
        self.description = description  # human-readable
        self.composition = composition  # non-primitive transformations may be
        # composed of other transformations
        self.is_input = not self.type.is_function()

    def instance(self, identifier: Optional[str] = None) -> Expr:
        if self.type.is_function():
            return Transformation(self)
        else:
            return Input(self, ident=identifier)


class TransformationAlgebra(object):
    def __init__(self, **signatures: Type):
        self.parser: Optional[pp.Parser] = None
        self.definitions: Dict[str, Definition] = {}

        for k, v in signatures.items():
            self.definitions[k] = Definition(name=k, type=v)

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return "\n".join(
            f"{k}: {v}" for k, v in self.definitions.items()) + "\n"

    def generate_parser(self) -> pp.Parser:

        ident = pp.Word(pp.alphanums + ':_').setName('identifier')

        expr = pp.MatchFirst(
            pp.CaselessKeyword(d.name) + pp.Optional(ident)
            if d.is_input else
            pp.CaselessKeyword(d.name)
            for d in self.definitions.values()
        ).setParseAction(
            lambda s, l, t: self.definitions[t[0]].instance(
                t[1] if len(t) > 1 else None)
        )

        return pp.infixNotation(expr, [(
            None, 2, pp.opAssoc.LEFT, lambda s, l, t: reduce(Result, t[0])
        )])

    def parse(self, string: str) -> Expr:
        if not self.parser:
            self.parser = self.generate_parser()
        expr = self.parser.parseString(string, parseAll=True)[0]
        return expr

    @staticmethod
    def from_dict(obj: Dict[str, Any]) -> TransformationAlgebra:
        """
        Create transformation algebra from an object, filtering out the
        relevant parts: those Type values whose keys start with lowercase.
        """
        return TransformationAlgebra(**{
            k.rstrip("_"): v for k, v in obj.items()
            if k[0].islower() and isinstance(v, Type)
        })

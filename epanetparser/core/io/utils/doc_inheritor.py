"""Utilitiy for inheriting docstrings."""
from typing import Iterable
import inspect


class DocInheritor:
    """
    Class decorator that copies method docstrings from a parent class.

    The decorator copies the ``__doc__`` attribute of selected methods from
    the immediate parent class to the corresponding methods of the decorated
    class. The method implementations themselves are not modified.

    Parameters
    ----------
    methods : iterable of str
        Names of methods whose docstrings should be inherited from the
        immediate parent class.

    Raises
    ------
    ValueError
        If the decorated class has no parent class, or if one of the
        specified methods does not exist on the parent class.

    Examples
    --------
    Define a base class with the desired documentation:

    >>> class Base:
    ...     def solve(self):
    ...         """"Solve the problem and return the result.""""
    ...         pass

    A subclass can override the method without duplicating its docstring:

    >>> @DocInheritor(["solve"])
    ... class Child(Base):
    ...     def solve(self):
    ...         pass

    The subclass retains its own implementation while inheriting the
    parent's documentation:

    >>> Child.solve.__doc__
    'Solve the problem and return the result.'
    """

    def __init__(self, methods: Iterable[str]):
        """
        Initialise the docstring inheritor.

        Parameters
        ----------
        methods : iterable of str
            Names of methods whose docstrings should be inherited.
        """
        self.methods = methods

    def __call__(self, cls):
        """
        Decorate a class by inheriting selected method docstrings.

        Parameters
        ----------
        cls : type
            Class whose methods should receive docstrings from its immediate
            parent class.

        Returns
        -------
        type
            The decorated class, unchanged apart from the updated method
            docstrings.

        Raises
        ------
        ValueError
            If the class has no parent class or a requested method is not
            defined by the parent class.
        """
        mro = inspect.getmro(cls)
        if len(mro) < 2:
            raise ValueError(
                f"Cannot determine parent class for {cls!r}"
            )
        parent = mro[1]

        for method_name in self.methods:
            if not hasattr(parent, method_name):
                raise ValueError(
                    f"Parent class {parent!r} does not have "
                    f"method {method_name!r}"
                )
            child_method = getattr(cls, method_name)
            parent_method = getattr(parent, method_name)
            child_method.__doc__ = parent_method.__doc__

        return cls
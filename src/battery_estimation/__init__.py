"""Battery SOC/SOH estimation reference implementation."""

from .models.ecm import ECMParameters, SecondOrderThevenin

__all__ = ["ECMParameters", "SecondOrderThevenin"]
__version__ = "1.1.0"

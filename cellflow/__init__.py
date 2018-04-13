"""Cellflow magic"""
__version__ = '0.0.1'

from .cellflow import Cellflow

def load_ipython_extension(ipython):
    ipython.register_magics(Cellflow)

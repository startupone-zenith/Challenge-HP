"""
Módulo web - Interface Flask e APIs
"""

from .flask_app import app, ScrapingJob, active_jobs

__all__ = [
    'app',
    'ScrapingJob', 
    'active_jobs'
]

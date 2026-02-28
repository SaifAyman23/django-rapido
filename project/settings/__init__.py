# Import base settings first
from .base import *

# Load environment-specific settings LAST (after all components)
if ENVIRONMENT == 'production':
    from .production import *
elif ENVIRONMENT == 'testing':
    from .testing import *
else:
    from .local import *
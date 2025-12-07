import sys
import os

# Asegurar que Python encuentra los módulos
sys.path.append(os.getcwd())



try:
    from app.modules.auth.tests.locustfile import AuthUser
except ImportError as e:
    print(f"Error importando AuthUser: {e}")

try:
    from app.modules.dataset.tests.locustfile import CommunityUser, DatasetUser
except ImportError as e:
    print(f"Error importando usuarios desde Dataset: {e}")

try:
    from app.modules.explore.tests.locustfile import ExploreUser
except ImportError as e:
    print(f"Error importando usuarios desde Explore: {e}")

CommunityUser.weight = 1
DatasetUser.weight = 1
ExploreUser.weight = 1
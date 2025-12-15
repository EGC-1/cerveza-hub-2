import sys
import os

sys.path.append(os.getcwd())

try:
    from app.modules.auth.tests.locustfile import AuthUser
except ImportError as e:
    print(f"Error importando AuthUser: {e}")

try:
    from app.modules.dataset.tests.locustfile import CommunityUser, DatasetUser, GithubDatasetUser, DownloadCounterUser#, StatsUser
except ImportError as e:
    print(f"Error importando usuarios desde Dataset: {e}")

try:
    from app.modules.explore.tests.locustfile import ExploreUser
except ImportError as e:
    print(f"Error importando usuarios desde Explore: {e}")

try:
    from app.modules.admin.tests.locustfile import AdminRoleUser
except ImportError as e:
    print(f"Error importando usuarios desde Admin: {e}")

CommunityUser.weight = 1
DatasetUser.weight = 1
ExploreUser.weight = 1
GithubDatasetUser.weight = 1
DownloadCounterUser.weight = 1
#StatsUser.weight = 1
AdminRoleUser.weight = 1
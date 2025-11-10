from app.modules.explore.repositories import ExploreRepository
from core.services.BaseService import BaseService


class ExploreService(BaseService):
    def __init__(self):
        super().__init__(ExploreRepository())

    def filter(self, query="", sorting="newest", publication_type="any", tags=[], community_id=None,**kwargs):
        return self.repository.filter(query, sorting, publication_type, tags, community_id=community_id, **kwargs)
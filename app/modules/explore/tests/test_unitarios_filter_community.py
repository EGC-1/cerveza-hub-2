import unittest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import or_
from flask import Flask 
from app.modules.explore.services import ExploreService
from app.modules.explore.repositories import ExploreRepository
from app.modules.dataset.models import DataSet, Community 

try:
    from app import app
except ImportError:
    app = Flask(__name__)


class ExploreServiceUnitTest(unittest.TestCase):
    
    @patch('app.modules.explore.services.ExploreRepository')
    def test_service_filter_calls_repository_with_community_id(self, MockRepo):

        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.filter.return_value = [] 
        
        service = ExploreService() 

        test_community_id = 5
        test_query = "data science" 
        test_sorting = "oldest"     
        test_publication_type = "article" 
        test_tags = ["ml", "ai"]    
        test_extra_arg = "extra"

        
        service.filter(
            query=test_query, 
            sorting=test_sorting, 
            publication_type=test_publication_type, 
            tags=test_tags, 
            community_id=test_community_id, 
            extra_arg=test_extra_arg
        )
        

        mock_repo_instance.filter.assert_called_once_with(
            test_query,                 
            test_sorting,               
            test_publication_type,      
            test_tags,                  
            community_id=test_community_id, 
            extra_arg=test_extra_arg
        )


    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()


        self.mock_model_query = MagicMock()
        self.mock_model_query.join.return_value = self.mock_model_query
        self.mock_model_query.filter.return_value = self.mock_model_query
        self.mock_model_query.order_by.return_value = self.mock_model_query
        self.mock_model_query.all.return_value = []
        

        self.patcher_dataset = patch.object(DataSet, 'query', new=self.mock_model_query)
        self.patcher_dataset.start()
        
        self.patcher_or = patch('app.modules.explore.repositories.or_', return_value=Mock(name='mock_or_clause'))
        self.mock_or = self.patcher_or.start()
        self.mock_communities = MagicMock()
        self.mock_communities.any.return_value = Mock(name='community_filter_clause_result')
        
        self.patcher_communities = patch.object(DataSet, 'communities', new=self.mock_communities)
        self.patcher_communities.start()
        
        self.repository = ExploreRepository()
        
        self.mock_filter = self.mock_model_query.filter
        self.mock_filter.reset_mock()


    def tearDown(self):
        self.patcher_dataset.stop()
        self.patcher_or.stop()
        self.patcher_communities.stop()
        self.app_context.pop() 

    def test_filter_by_community_id_applies_correct_clause(self):

        test_community_id = 3
        
        self.repository.filter(community_id=str(test_community_id))
        
        self.mock_communities.any.assert_called_once()
        
        self.assertIsInstance(self.mock_communities.any.call_args[0][0], 
                              type(Community.id == test_community_id), 
                              "El argumento de .any() no es un objeto de expresión SQL.")
        
        expected_filter_clause = self.mock_communities.any.return_value
        
        found_filter_call = any(
            call_args[0] == expected_filter_clause
            for call_args, _ in self.mock_filter.call_args_list
        )
        
        self.assertTrue(found_filter_call, "El resultado de DataSet.communities.any() no se pasó a query.filter().")
        self.assertEqual(self.mock_filter.call_count, 3, "Se esperaban 3 llamadas a filter (or, doi, community).")
        
    def test_filter_by_community_id_not_applied_for_none(self):

        self.repository.filter(community_id=None)
        
        self.mock_communities.any.assert_not_called()
        self.assertEqual(self.mock_filter.call_count, 2)
        
    def test_filter_by_community_id_not_applied_for_empty_string(self):

        self.repository.filter(community_id="")
        
        self.mock_communities.any.assert_not_called()
        self.assertEqual(self.mock_filter.call_count, 2)

    def test_filter_by_community_id_handles_invalid_int(self):

        self.repository.filter(community_id="abc")
        
        self.mock_communities.any.assert_not_called()
        self.assertEqual(self.mock_filter.call_count, 2)
        
    def test_filter_by_community_id_handles_zero(self):

        self.repository.filter(community_id="0")
        
        self.mock_communities.any.assert_not_called()
        self.assertEqual(self.mock_filter.call_count, 2)

if __name__ == '__main__':
    unittest.main()
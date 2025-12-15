
import pytest
import sys
import os

from fakenodo.app import app, DEPOSITS

@pytest.fixture(scope="function")
def client():
    """
    Crea un cliente de pruebas para Flask y GARANTIZA EL AISLAMIENTO.
    Se ejecuta antes de CADA función de test (scope='function').
    """
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        DEPOSITS.clear() 
        print(f"\n[Fixture] Memoria limpia. Depósitos actuales: {len(DEPOSITS)}")
        
        yield client  
        
        DEPOSITS.clear()
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importa tu aplicación de FastAPI y la configuración de la base de datos
from src.main import app
from src.database.database import Base, get_db

# --- CONFIGURACIÓN DE LA BASE DE DATOS DE PRUEBA ---
# Usamos una base de datos SQLite en memoria. Es la forma más rápida y limpia
# para las pruebas, ya que se crea desde cero cada vez que se ejecutan los tests.
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Creamos el motor de la base de datos de prueba.
# `connect_args={"check_same_thread": False}` es necesario para SQLite.
# `poolclass=StaticPool` es recomendado para SQLite en memoria para asegurar
# que todos los accesos usen la misma conexión.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Creamos una fábrica de sesiones de prueba que usaremos en las fixtures.
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Fixture a nivel de sesión para crear todas las tablas una vez.
    `autouse=True` asegura que se ejecute automáticamente.
    """
    # Borra y recrea las tablas al inicio de la sesión de pruebas
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Fixture a nivel de función que proporciona una sesión de base de datos limpia
    para cada test individual.
    
    Utiliza una transacción que se revierte al final del test, garantizando
    un aislamiento completo.
    """
    # Establece una conexión y comienza una transacción anidada.
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session  # El test se ejecuta aquí, usando esta sesión.

    # Al finalizar el test, cerramos la sesión y revertimos la transacción.
    session.close()
    transaction.rollback() # ¡La clave del aislamiento!
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    Fixture a nivel de función que proporciona un `TestClient` de FastAPI.
    
    Este cliente está configurado para usar la base de datos de prueba aislada
    gracias a la sobrescritura de la dependencia `get_db`.
    """
    def override_get_db():
        """
        Una función "override" que reemplaza la dependencia `get_db`
        de la aplicación principal para inyectar nuestra sesión de prueba.
        """
        try:
            yield db_session
        finally:
            db_session.close()

    # Aplica la sobrescritura a la aplicación de FastAPI
    app.dependency_overrides[get_db] = override_get_db

    # Proporciona el cliente de prueba al test
    yield TestClient(app)

    # Limpia la sobrescritura después de que el test haya terminado
    del app.dependency_overrides[get_db]
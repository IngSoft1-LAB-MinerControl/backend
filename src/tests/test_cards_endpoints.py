"""
Tests for the Card endpoints, refactored to use Pytest fixtures.
Each test sets up its own specific, isolated state.
"""
from unittest.mock import patch, AsyncMock
import pytest
import datetime

# Importamos los modelos que usaremos para crear datos de prueba
from src.database.models import Event, Game, Player, Detective, Card

# --- Tests para Listar Cartas ---

def test_list_cards_in_game_success(client, db_session):
    """Verifica que se pueden listar las cartas de una partida existente."""
    # Arrange: Crear un juego, un jugador y una carta asociada al juego
    game = Game(name="Test Game", status="in course", max_players=4, min_players=2, players_amount=1, current_turn = 1)
    player = Player(name="P1", game=game, birth_date=datetime.date(2000,1,1), turn_order=1)
    card = Detective(card_id=1, type="detective", name="Parker Pyne", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=2)
    db_session.add_all([game, player, card])
    db_session.commit()

    # Act
    response = client.get(f"/lobby/cards/{game.game_id}")

    # Assert
    assert response.status_code == 200
    cards = response.json()
    assert isinstance(cards, list)
    assert len(cards) == 1
    assert cards[0]["card_id"] == 1

def test_list_cards_in_game_not_found(client):
    """Verifica que devuelve 404 si no hay cartas para una partida."""
    # Arrange: Crear solo un juego, sin cartas
    game_resp = client.post("/games", json={"name": "Empty Game", "min_players": 2, "max_players": 4, "status" : "waiting players"})
    game_id = game_resp.json()["game_id"]
    
    # Act
    response = client.get(f"/lobby/cards/{game_id}")
    
    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "No cards found for the given game_id"

def test_list_cards_of_player_success(client, db_session):
    """Verifica que se pueden listar las cartas de la mano de un jugador."""
    # Arrange: Crear un juego, jugador y una carta en la mano del jugador
    game = Game(name="Test Game", status="in course", max_players=4, min_players=2, players_amount=1)
    player = Player(name="P1", game=game, birth_date=datetime.date(2000,1,1), turn_order=1)
    db_session.add_all([game, player])
    db_session.commit()
    print(player.player_id)
    card = Detective(card_id=1, type="detective", name="Parker Pyne", picked_up=True, dropped=False, player_id=player.player_id, game_id=1, quantity_set=2)
    db_session.add(card)
    db_session.commit()

    # Act
    response = client.get(f"/lobby/list/cards/{player.player_id}")

    # Assert
    
    assert response.status_code == 200
    cards = response.json()
    assert isinstance(cards, list)
    assert len(cards) == 1
    assert cards[0]["player_id"] == 1
  

# --- Tests para Recoger una Carta (Pick Up) ---
def test_pickup_a_card_success(client, db_session):
    """
    Test del caso de éxito: un jugador roba una carta de un mazo con cartas disponibles.
    
    Verifica:
    - Que la respuesta sea un 200 OK.
    - Que la carta robada se asigne correctamente al jugador.
    - Que el estado de la carta (`picked_up`) se actualice en la BBDD.
    - Que el contador de cartas del juego (`cards_left`) se decremente.
    - Que la función asíncrona de broadcast sea llamada.
    """
    # --- 1. Arrange: Preparar el estado inicial ---
    # Crear un juego
    test_game = Game(
        name="Partida de Prueba", 
        max_players=4, 
        min_players=2, 
        players_amount=1, 
        cards_left=10 # El mazo tiene 10 cartas
    )
    db_session.add(test_game)
    db_session.commit()

    game_id = test_game.game_id

    # Crear un jugador en esa partida
    test_player = Player(
        name="Jugador 1", 
        game_id=test_game.game_id, 
        birth_date=datetime.date(2000, 1, 1)
    )
    db_session.add(test_player)
    db_session.commit()
    player_id = test_player.player_id

    # Crear una carta disponible en el mazo de esa partida
    card_in_deck = Detective(
        name="Sherlock",
        game_id=test_game.game_id,
        picked_up=False,
        dropped=False,
        draft=False
    )
    db_session.add(card_in_deck)
    db_session.commit()
    card_id = card_in_deck.card_id
    
    # Refrescar objetos para obtener sus IDs generadas por la BBDD
    db_session.refresh(test_game)
    db_session.refresh(test_player)
    db_session.refresh(card_in_deck)

    # Mockear (simular) la función asíncrona para que el test no falle
    with patch('src.routes.cards_routes.broadcast_game_information', new_callable=AsyncMock) as mock_broadcast:
        # --- 2. Act: Ejecutar la acción a probar ---
        response = client.put(f"/cards/pick_up/{test_player.player_id},{test_game.game_id}")

        # --- 3. Assert: Verificar los resultados ---
        # Verificar la respuesta HTTP
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["card_id"] == card_id
        assert response_data["player_id"] == player_id
        assert response_data["picked_up"] is True

        # Verificar el estado de la base de datos
        updated_card = db_session.query(Card).filter(Card.card_id == card_id).one()
        updated_game = db_session.query(Game).filter(Game.game_id == game_id).one()
        
        # Ahora, hacemos las aserciones sobre los objetos recién consultados.
        assert updated_card.player_id == player_id
        assert updated_card.picked_up is True
        assert updated_game.cards_left == 0 # El contador debe bajar de 5 a 4.

        # Verificar que la función de broadcast fue llamada
        mock_broadcast.assert_awaited_once_with(game_id)

    
@patch('src.routes.cards_routes.only_6') 
def test_pickup_a_card_hand_full(mock_only_6, client, db_session):
    """
    Verifica que un jugador con 6 cartas no puede recoger otra.
    Usa patch para simular directamente el resultado de la validación 'only_6'.
    """
    # Arrange: Configura el mock para que devuelva True, simulando que la mano está llena.
    mock_only_6.return_value = True

    # Solo necesitamos crear un juego y un jugador para que el endpoint tenga IDs válidos.
    # Ya NO necesitamos crear las 6 cartas en la DB, el mock se encarga de la lógica.
    game = Game(name="Test Game", status="in course", max_players=4, min_players=2, players_amount=1)
    player = Player(name="P1", game=game, birth_date=datetime.date(2000, 1, 1), turn_order=1)
    db_session.add_all([game, player])
    db_session.commit()
    
    # Act
    response = client.put(f"/cards/pick_up/{player.player_id},{game.game_id}")

    # Assert
    # 1. Verificar que el mock fue llamado correctamente
    mock_only_6.assert_called_once_with(player.player_id, db_session)
    
    # 2. Verificar que la API devolvió el error esperado
    assert response.status_code == 400
    assert "already has 6 cards" in response.json()["detail"]


@patch('src.routes.cards_routes.broadcast_last_discarted_cards')
def test_discard_card_success(mock_broadcast, client, db_session):
    """Verifica que un jugador puede descartar la carta correcta."""
    # Arrange: Crear juego, jugador y una carta específica en su mano
    game = Game(name="Test Game", status="in course", max_players=4, min_players=2, players_amount=1)
    db_session.add(game)
    db_session.commit()
    player = Player(name="P1", game_id=game.game_id, birth_date=datetime.date(2000,1,1), turn_order=1)
    db_session.add(player)
    db_session.commit()
    player_id = player.player_id
    card_in_hand =  Detective(card_id=99, type="detective", name="Parker Pyne", picked_up=False, dropped=False, player_id=player.player_id, game_id=game.game_id, quantity_set=2)
    db_session.add( card_in_hand)
    db_session.commit()
    print(player.turn_order)

    # Act
    # Asumiendo que la API necesita saber qué carta descartar
    response = client.put(f"/cards/drop/{player_id}")
    
    # Assert
    if response.status_code != 200:
        print("DEBUG - Mensaje de error de la API:", response.json())

    assert response.status_code == 200
    data = response.json()
    assert data["card_id"] == card_in_hand.card_id
    assert data["dropped"] is True
    assert data["picked_up"] is False # Asumiendo que `picked_up` se pone en False
    mock_broadcast.assert_awaited_once_with(player_id)

"""
Tests for the Event endpoints and services, using pytest fixtures for isolation.
"""
import datetime
import pytest
from unittest.mock import patch, AsyncMock

# Import models needed for setting up test data
from src.database.models import Game, Player, Event, Secrets, Detective, Card

@pytest.fixture
def setup_events_data(db_session):
    """
    Fixture to create a consistent set of data for event-related tests.
    This runs for each test, ensuring a clean state.
    """
    # Arrange: Create a game, players, and various cards/secrets for event scenarios
    game = Game(game_id=1, name="Event Test Game", status="in course", max_players=4, min_players=2, players_amount=2, cards_left=10)
    
    # Player 1: Has a "Not so fast" card to test 'cards_off_table'
    player1 = Player(player_id=1, name="Event Player 1", host=True, birth_date=datetime.date(2000, 1, 1), game_id=1, turn_order=1)
    nsf_card = Event(card_id=1, name="Not so fast", type="event", picked_up=True, dropped=False, player_id=1, game_id=1)

    # Player 2: Target for events
    player2 = Player(player_id=2, name="Event Player 2", host=False, birth_date=datetime.date(2001, 1, 1), game_id=1, turn_order=2)

    # A revealed secret for the 'one_more' event
    revealed_secret = Secrets(secret_id=1, murderer=False, acomplice=False, revelated=True, player_id=1, game_id=1)

    # A card in the discard pile for 'look_into_ashes'
    discarded_card = Detective(card_id=2, name="Hercule Poirot", type="detective", picked_up=True, dropped=True, player_id=1, game_id=1, quantity_set=3, discardInt=1)
    
    # Cards in the deck for 'early_train_paddington'
    deck_cards = [Detective(name=f"Deck Card {i}", type="detective", game_id=1, quantity_set=1) for i in range(10)]

    db_session.add_all([game, player1, player2, nsf_card, revealed_secret, discarded_card] + deck_cards)
    db_session.commit()


# --- Tests for 'Cards off the table' Event ---

@pytest.mark.asyncio
@patch('src.routes.event_routes.broadcast_last_discarted_cards', new_callable=AsyncMock)
@patch('src.routes.event_routes.broadcast_game_information', new_callable=AsyncMock)
async def test_cards_off_table_success(mock_broadcast_game, mock_broadcast_discard, client, setup_events_data, db_session):
    """Verifica que el evento 'Cards off the table' descarta las cartas 'Not so fast'."""
    # Act: Player 1 activates the event
    response = client.put("/event/cards_off_table/1")

    # Assert
    assert response.status_code == 200
    
    # Verify in DB that the card is now dropped
    card = db_session.query(Event).filter(Event.card_id == 1).first()
    assert card.dropped is True

@pytest.mark.asyncio
async def test_cards_off_table_player_not_found(client):
    """Verifica el error cuando el jugador no existe."""
    response = client.put("/event/cards_off_table/999")
    assert response.status_code == 404
    assert "Player not found" in response.json()["detail"]

@pytest.mark.asyncio
@patch('src.routes.event_routes.broadcast_last_discarted_cards', new_callable=AsyncMock)
@patch('src.routes.event_routes.broadcast_game_information', new_callable=AsyncMock)
async def test_cards_off_table_no_nsf_cards(mock_broadcast_game, mock_broadcast_discard, client, setup_events_data):
    """Verifica que no ocurre error si el jugador no tiene cartas 'Not so fast'."""
    # Act: Player 2 (who has no NSF cards) activates the event
    response = client.put("/event/cards_off_table/2")
    
    # Assert
    assert response.status_code == 200
    assert "No 'Not so fast' cards found" in response.json()["message"]


# --- Tests for 'One More' Event ---

@pytest.mark.asyncio
@patch('src.routes.event_routes.broadcast_game_information', new_callable=AsyncMock)
async def test_one_more_success(mock_broadcast, client, setup_events_data):
    """Verifica que el evento 'One More' reasigna un secreto revelado."""
    # Act: Give the revealed secret (ID 1) to Player 2
    response = client.put("/event/one_more/2,1")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["player_id"] == 2
    assert data["revelated"] is False # The secret should now be hidden

@pytest.mark.asyncio
async def test_one_more_secret_not_found_or_not_revealed(client, setup_events_data):
    """Verifica el error si el secreto no existe o no está revelado."""
    # Act: Try to use a non-existent secret
    response = client.put("/event/one_more/2,999")
    assert response.status_code == 404
    assert "Secret not found or is not revealed" in response.json()["detail"]


# --- Tests for 'Early Train to Paddington' Event ---

@pytest.mark.asyncio
@patch('src.routes.event_routes.broadcast_last_discarted_cards', new_callable=AsyncMock)
@patch('src.routes.event_routes.broadcast_game_information', new_callable=AsyncMock)
async def test_early_train_paddington_success(mock_broadcast_game, mock_broadcast_discard, client, setup_events_data, db_session):
    """Verifica que el evento descarta 6 cartas del mazo."""
    # Act
    response = client.put("/event/early_train_paddington/1")

    # Assert
    assert response.status_code == 200
    assert "event executed successfully" in response.json()["message"]
    
    # Verify in DB
    discarded_count = db_session.query(Card).filter(Card.game_id == 1, Card.dropped == True).count()
    # 1 from setup + 6 from event
    assert discarded_count == 7

@pytest.mark.asyncio
async def test_early_train_paddington_game_not_found(client):
    """Verifica el error si la partida no existe."""
    response = client.put("/event/early_train_paddington/999")
    assert response.status_code == 404
    assert "Game not found" in response.json()["detail"]

@pytest.mark.asyncio
@patch('src.database.services.services_events.finish_game', new_callable=AsyncMock)
@patch('src.routes.event_routes.broadcast_last_discarted_cards', new_callable=AsyncMock)
@patch('src.routes.event_routes.broadcast_game_information', new_callable=AsyncMock)
async def test_early_train_paddington_not_enough_cards(mock_broadcast_game, mock_broadcast_discard, mock_finish_game, client, db_session):
    """Verifica que el juego termina si no hay suficientes cartas para descartar."""
    # Arrange: Create a game with only 5 cards in the deck
    game = Game(game_id=2, name="Short Deck Game", status="in course", max_players=2, min_players=2, players_amount=2)
    deck_cards = [Detective(name=f"Deck Card {i}", type="detective", game_id=2, quantity_set=1) for i in range(5)]
    db_session.add(game)
    db_session.add_all(deck_cards)
    db_session.commit()

    # Act
    response = client.put("/event/early_train_paddington/2")

    # Assert
    assert response.status_code == 200
    assert "Not enough cards" in response.json()["message"]
    mock_finish_game.assert_called_once_with(2)


# --- Tests for 'Look into the ashes' Event ---

@pytest.mark.asyncio
@patch('src.routes.event_routes.broadcast_last_discarted_cards', new_callable=AsyncMock)
@patch('src.routes.event_routes.broadcast_game_information', new_callable=AsyncMock)
async def test_look_into_ashes_success(mock_broadcast_game, mock_broadcast_discard, client, setup_events_data):
    """Verifica que un jugador puede tomar una carta de la pila de descarte."""
    # Act: Player 2 takes the discarded card (ID 2)
    response = client.put("/event/look_into_ashes/2,2")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["player_id"] == 2
    assert data["dropped"] is False

@pytest.mark.asyncio
async def test_look_into_ashes_card_not_in_discard_pile(client, setup_events_data):
    """Verifica el error si la carta no está en la pila de descarte."""
    # Card 1 is in a player's hand, not discarded
    response = client.put("/event/look_into_ashes/2,1")
    assert response.status_code == 404
    assert "Card not found" in response.json()["detail"]
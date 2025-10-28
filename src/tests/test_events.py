"""
Tests for the Event endpoints and services, using pytest fixtures for isolation.
"""
import datetime
import pytest
from unittest.mock import patch, AsyncMock

# Import models needed for setting up test data
from src.database.database import get_db
from src.database.models import Game, Player, Event, Secrets, Detective, Card

@pytest.fixture
def setup_events_data(db_session):
    """
    Fixture to create a consistent set of data for event-related tests.
    This runs for each test, ensuring a clean state.
    """
    # Arrange: Create a game, players, and various cards/secrets for event scenarios
    game = Game(game_id=1, name="Event Test Game", status="in course", max_players=4, min_players=2, players_amount=3, cards_left=10)
    
    # Player 1: Has a "Not so fast" card and a card for trading
    player1 = Player(player_id=1, name="Event Player 1", host=True, birth_date=datetime.date(2000, 1, 1), game_id=1, turn_order=1, social_disgrace=False, isSelected=False)
    nsf_card = Event(card_id=1, name="Not so fast", type="event", picked_up=True, dropped=False, player_id=1, game_id=1)
    p1_card = Detective(card_id=3, name="Card for P1", type="detective", player_id=1, game_id=1)

    # Player 2: Target for events and has a card for trading
    player2 = Player(player_id=2, name="Event Player 2", host=False, birth_date=datetime.date(2001, 1, 1), game_id=1, turn_order=2, social_disgrace=False, isSelected=False)
    p2_card = Detective(card_id=4, name="Card for P2", type="detective", player_id=2, game_id=1)


    # A revealed secret for the 'one_more' event
    revealed_secret = Secrets(secret_id=1, murderer=False, acomplice=False, revelated=True, player_id=1, game_id=1)

    # A card in the discard pile for 'look_into_ashes'
    discarded_card = Detective(card_id=2, name="Hercule Poirot", type="detective", picked_up=True, dropped=True, player_id=1, game_id=1, quantity_set=3, discardInt=1)
    
    # Cards in the deck for 'early_train_paddington'
    deck_cards = [Detective(name=f"Deck Card {i}", type="detective", game_id=1, quantity_set=1) for i in range(10)]

    db_session.add_all([game, player1, player2, nsf_card, p1_card, p2_card, revealed_secret, discarded_card] + deck_cards)
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
    response.status_code == 200
    
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

@pytest.mark.asyncio 
@patch('src.routes.event_routes.broadcast_last_discarted_cards', new_callable=AsyncMock)
@patch('src.routes.event_routes.broadcast_game_information', new_callable=AsyncMock)
async def test_delay_murderers_escape (mock_broadcast_game, mock_broadcast_discard, client, setup_events_data, db_session) : 
    game = Game(game_id=2, name="Short Deck Game", status="in course", max_players=2, min_players=2, players_amount=2, cards_left = 46)
    db_session.add(game) 
    db_session.commit()
    
    card1 = Event(name="C1", player_id=None, game_id=game.game_id, picked_up=True, dropped=True)
    card2 = Event(name="C2", player_id=None, game_id=game.game_id, picked_up=True, dropped=True)
    db_session.add_all([card1, card2]) 
    db_session.commit()
    card_ids_to_delay = [card1.card_id, card2.card_id]

    response = client.put(
        f"/event/delay_escape/{game.game_id}",
        json={"card_ids": card_ids_to_delay}
    )
    assert response.status_code == 200 
    data = response.json()
    assert data[0]["dropped"] is False 
    assert data[1]["dropped"] is False 
    assert data[0]["picked_up"] is False 
    assert data[1]["picked_up"] is False 
    assert data[0]["discardInt"] == -1  
    assert data[1]["discardInt"] == -1

@pytest.mark.asyncio
async def test_card_trade_initiate_success(client, setup_events_data, mocker):
    """Verifica que el Step 1 del 'Card Trade' selecciona a los jugadores correctamente."""
    mock_broadcast = mocker.patch('src.routes.event_routes.broadcast_game_information', new_callable=AsyncMock)
    
    # Act
    response = client.post("/event/card_trade/initiate/1,2")
    
    # Assert
    assert response.status_code == 200
    assert "Card trade initiated" in response.json()["message"]
    
    # Verify in DB
    db = client.app.dependency_overrides[get_db]().__next__()
    player1 = db.query(Player).filter(Player.player_id == 1).first()
    player2 = db.query(Player).filter(Player.player_id == 2).first()
    assert player1.isSelected is True
    assert player2.isSelected is True
    mock_broadcast.assert_awaited_once_with(1)

@pytest.mark.asyncio
async def test_card_trade_initiate_player_not_found(client, setup_events_data):
    """Verifica el error si uno de los jugadores en la iniciación no existe."""
    response = client.post("/event/card_trade/initiate/1,999")
    assert response.status_code == 404
    assert "One or both players not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_card_trade_finalize_success(client, setup_events_data, mocker):
    """Verifica que el Step 2 del 'Card Trade' intercambia las cartas y resetea el estado."""
    mock_broadcast = mocker.patch('src.routes.event_routes.broadcast_game_information', new_callable=AsyncMock)
    
    # Arrange: Manually set the 'isSelected' state as if Step 1 happened
    db = client.app.dependency_overrides[get_db]().__next__()
    player1_before = db.query(Player).filter(Player.player_id == 1).first()
    player2_before = db.query(Player).filter(Player.player_id == 2).first()
    player1_before.isSelected = True
    player2_before.isSelected = True
    db.commit()

    print(f"\n[ANTES] Player 1 isSelected: {player1_before.isSelected}")
    print(f"[ANTES] Player 2 isSelected: {player2_before.isSelected}")

    # Act
    response = client.post("/event/card_trade/finalize/1,2,3,4")
    
    # Assert
    assert response.status_code == 200
    assert "Card trade finalized successfully" in response.json()["message"]
    
    # --- VERIFICACIÓN ---
    # Vuelve a pedir los objetos a la BD para obtener su estado actualizado
    player1_after = db.query(Player).filter(Player.player_id == 1).first()
    player2_after = db.query(Player).filter(Player.player_id == 2).first()
    
    print(f"[DESPUÉS] Player 1 isSelected: {player1_after.isSelected}")
    print(f"[DESPUÉS] Player 2 isSelected: {player2_after.isSelected}")

    # Verify card owners in DB
    card_from_p1 = db.query(Card).filter(Card.card_id == 3).first()
    card_from_p2 = db.query(Card).filter(Card.card_id == 4).first()
    assert card_from_p1.player_id == 2
    assert card_from_p2.player_id == 1
    
    # Verify players are unselected
    assert player1_after.isSelected is False
    assert player2_after.isSelected is False
    mock_broadcast.assert_awaited_once_with(1)

@pytest.mark.asyncio
async def test_card_trade_finalize_invalid_card_owner(client, setup_events_data):
    """Verifica el error si una de las cartas no pertenece al jugador correcto."""
    # Arrange: Manually set state
    db = client.app.dependency_overrides[get_db]().__next__()
    p1 = db.query(Player).filter(Player.player_id == 1).first()
    p2 = db.query(Player).filter(Player.player_id == 2).first()
    p1.isSelected = True
    p2.isSelected = True
    db.commit()
    
    # Act: Try to trade P2's card (4) as if it were P1's
    response = client.post("/event/card_trade/finalize/1,2,4,3")

    # Assert
    assert response.status_code == 404
    assert "Invalid player or card IDs provided" in response.json()["detail"]

"""
main.py

Handles ASCII board rendering, Piece selection, movement, and managing the game loop.
"""

from __future__ import annotations
from typing import Optional

from gamelogic import GameState, notationToPos, posToNotation
from pieces import PROMOTABLE_PIECES

borderDivider: str = "  ——" + "—————" * 7
whiteCell: str = "░░░"
darkCell: str = "    "
highlightCell: str = " ⊙ "

# renderBoard builds the ASCII board string. Perspective flips row/column ordering for black's view.
# Highlighted squares (legal moves) are shown with a ⊙ marker.

def renderBoard(
    game: GameState,
    perspective: str,
    highlights: Optional[list[tuple[int, int]]] = None,
) -> str:
    hi = set(highlights or [])

    if perspective == "white":
        rowOrder = range(8)
        colOrder = list(range(8))
        fileStr = "ABCDEFGH"
    else:
        rowOrder = range(7, -1, -1)
        colOrder = list(range(7, -1, -1))
        fileStr = "HGFEDCBA"

    lines = [borderDivider]

    for row in rowOrder:
        rank = str(8 - row)
        rowStr = f"{rank} "

        for col in colOrder:
            piece = game.grid[row][col]

            if (row, col) in hi:
                cell = highlightCell
            elif piece is not None:
                cell = f" {piece.symbol} "
            else:
                cell = whiteCell if (row + col) % 2 == 0 else darkCell

            rowStr += "|" + cell

        rowStr += "|"
        lines.append(rowStr)
        lines.append(borderDivider)

    labelLine = "   " + "    ".join(fileStr)
    lines.append(labelLine)

    return "\n".join(lines)

# movesAsNotation converts a list of (row, col) tuples to a list of square names.

def movesAsNotation(moves: list[tuple[int, int]]) -> list[str]:
    return sorted(posToNotation(r, c) for r, c in moves)

# announceEnd prints a game over message based on the game status.

def announceEnd(status: str, loserColor: str) -> None:
    winner = "Black" if loserColor == "white" else "White"
    if status == "checkmate":
        print(f"\n  ♛  Checkmate!  {winner} wins!  ♛\n")
    else:
        print("\n  ½  Stalemate – the game is a draw.  ½\n")

# printHeader prints the ASCII chess header.

def printHeader() -> None:
    border = "═" * 44
    print(f"\n  ╔{border}╗")
    print("  ║       ♜  A S C I I   C H E S S  ♖         ║")
    print(f"  ╚{border}╝")
    print("  Commands to remember:")
    print("    takeback – undo the last move")
    print("    back     – (during move selection) re-pick piece")
    print("    quit     – exit the game\n")

# The game loop runs as a simple state machine with four states
# SELECTING_PIECE prompts the player to pick one of their pieces, validates the input, and checks that it has legal moves.
# SELECTING_DEST shows available destinations for the selected piece and applies the chosen move.
# PROMOTION prompts for a promotion choice after a pawn reaches the back rank.
# GAME_OVER is self-explanatory. The loop exits.

class State:
    SELECTING_PIECE = "selecting_piece"
    SELECTING_DEST = "selecting_dest"
    PROMOTION = "promotion"
    GAME_OVER = "game_over"

# handleSelectingPiece is the default state at the start of every turn.
# It first checks if the game is already over (checkmate/stalemate), and if so, announces the result and moves to GAME_OVER.
# It renders the board and prompts the player to pick a piece.
# Then validates the input, checking that it's a real square and that the piece is owned by the current player.
# Upon success, it stores the chosen piece and its legal moves in context, and moves to SELECTING_DEST.
# Also handles 'takeback' and 'quit' commands.

def handleSelectingPiece(
    game: GameState,
    context: dict,
) -> str:
    color = game.currentTurn
    status = game.gameStatus(color)

    if status in ("checkmate", "stalemate"):
        print("\n" + renderBoard(game, color) + "\n")
        announceEnd(status, color)
        return State.GAME_OVER
    print("\n" + renderBoard(game, color) + "\n")
    if status == "check":
        print("    You are in check!")
    raw = input(
        f"  {color.capitalize()}'s turn. "
        "Which piece to move? (or 'takeback' / 'quit'): ").strip()

    cmd = raw.lower()

    if cmd == "quit":
        print("  Thanks for playing!")
        return State.GAME_OVER

    if cmd == "takeback":
        if game.takeback():
            print("  Move taken back.\n")
        else:
            print("  No moves to take back yet.\n")
        return State.SELECTING_PIECE

    pos = notationToPos(raw)
    if pos is None:
        print(f"  ✗  '{raw.upper()}' is not a valid square. Use notation like 'E2'.")
        return State.SELECTING_PIECE

    piece = game.grid[pos[0]][pos[1]]

    if piece is None:
        print(f"  ✗  {raw.upper()} is empty. Choose a square with one of your pieces.")
        return State.SELECTING_PIECE

    if piece.color != color:
        print(
            f"  ✗  {raw.upper()} holds a {piece.color} {piece.name}. "
            f"It is {color}'s turn.")
        return State.SELECTING_PIECE

    legalMoves = game.legalMovesFor(piece)
    if not legalMoves:
        reason = " while you are in check" if status == "check" else ""
        print(
            f"  ✗  {raw.upper()} contains a {piece.name} "
            f"with no legal moves{reason}.")
        return State.SELECTING_PIECE

    context["selectedPiece"] = piece
    context["selectedMoves"] = legalMoves
    return State.SELECTING_DEST

# handleSelectingDest is the state after the player has selected a piece and its legal moves.
# It renders the board and prompts the player to select a destination.
# Then validates the input, checking that it's a legal move.
# If that works, then it applies the move and switches to SELECTING_PIECE or PROMOTION, depending on whether the move is a promotion.
# Also handles 'back' and 'quit' commands.

def handleSelectingDest(
    game: GameState,
    context: dict,
) -> str:
    piece = context["selectedPiece"]
    moves = context["selectedMoves"]
    color = game.currentTurn
    fromNotation = posToNotation(*piece.position)
    strs = movesAsNotation(moves)

    print(f"\n  {fromNotation} → {piece.name}  |  Available moves: {', '.join(strs)}")
    print("\n" + renderBoard(game, color, highlights=moves) + "\n")

    raw = input(
        f"  Where to move the {piece.name}? "
        f"(Available: {', '.join(strs)} | 'back' / 'takeback' / 'quit'): ").strip()

    cmd = raw.lower()

    if cmd == "quit":
        print("  Thanks for playing!")
        context["selectedPiece"] = None
        context["selectedMoves"] = []
        return State.GAME_OVER

    if cmd in ("back", "cancel"):
        context["selectedPiece"] = None
        context["selectedMoves"] = []
        return State.SELECTING_PIECE

    if cmd == "takeback":
        if game.takeback():
            print("  Move taken back.\n")
        else:
            print("  No moves to take back yet.\n")
        context["selectedPiece"] = None
        context["selectedMoves"] = []
        return State.SELECTING_PIECE

    dest = notationToPos(raw)
    if dest is None or dest not in moves:
        print(
            f"  ✗  '{raw.upper()}' is not a valid destination. "
            f"Choose from: {', '.join(strs)}"
        )
        return State.SELECTING_DEST

    toNotation = posToNotation(*dest)
    needsPromotion = game.applyMove(piece, dest)

    print(f"\n  ✓  {fromNotation} {piece.name} → {toNotation}.")

    context["selectedPiece"] = None
    context["selectedMoves"] = []

    if needsPromotion:
        context["promotingPawn"] = piece
        return State.PROMOTION

    newStatus = game.gameStatus(game.currentTurn)
    if newStatus == "check":
        print(f"  ⚠  {game.currentTurn.capitalize()} is now in check!")

    return State.SELECTING_PIECE

# handlePromotion is the state after a pawn reaches the back rank.
# It prompts the player to choose a piece for the pawn.
# Then validates the input, checking that it's a valid piece.
# Validates the choice and calls applyPromotion() to replace the pawn on the board.
# Checks if the opponent is now in check and switches to SELECTING_PIECE.
# Also handles 'back' and 'quit' commands.

def handlePromotion(
    game: GameState,
    context: dict,
) -> str:
    pawn = context["promotingPawn"]
    color = pawn.color
    valid = list(PROMOTABLE_PIECES.keys())

    print(f"\n  ★  Pawn promotion! Choose a piece for {color}:")
    print(f"     {' | '.join(valid)}")

    raw = input("  Promote to: ").strip()
    choice = raw.capitalize()

    if choice not in valid:
        print(f"  ✗  '{raw}' is not valid. Choose from: {', '.join(valid)}")
        return State.PROMOTION

    game.applyPromotion(pawn, choice)
    print(f"  ✓  Pawn promoted to {choice}!")

    context["promotingPawn"] = None

    postStatus = game.gameStatus(game.currentTurn)
    if postStatus == "check":
        print(f"  ⚠  {game.currentTurn.capitalize()} is now in check!")

    return State.SELECTING_PIECE

# runGame runs the main game loop.

def runGame() -> None:
    game = GameState()
    state = State.SELECTING_PIECE
    gameActive = True

    context: dict = {
        "selectedPiece": None,
        "selectedMoves": [],
        "promotingPawn": None,
    }

    handlers = {
        State.SELECTING_PIECE: handleSelectingPiece,
        State.SELECTING_DEST: handleSelectingDest,
        State.PROMOTION: handlePromotion,
    }

    printHeader()

    while gameActive:
        handler = handlers.get(state)

        if handler is None:
            gameActive = False
        else:
            nextState = handler(game, context)
            state = nextState
            gameActive = state != State.GAME_OVER

if __name__ == "__main__":
    runGame()
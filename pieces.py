"""
pieces.py

Defines all chess piece classes and the data structures that support them.
This is the foundation the rest of the codebase builds on.
"""

from __future__ import annotations
from typing import Optional


UNICODE_PIECES: dict[tuple[str, str], str] = {
    ("white", "King"): "♔",
    ("white", "Queen"): "♕",
    ("white", "Rook"): "♖",
    ("white", "Bishop"): "♗",
    ("white", "Knight"): "♘",
    ("white", "Pawn"): "♙",
    ("black", "King"): "♚",
    ("black", "Queen"): "♛",
    ("black", "Rook"): "♜",
    ("black", "Bishop"): "♝",
    ("black", "Knight"): "♞",
    ("black", "Pawn"): "♟",
}


PROMOTABLE_PIECES: dict[str, type] = {}


def inBounds(row: int, col: int) -> bool:
    return 0 <= row < 8 and 0 <= col < 8

def slidingMoves(
    piece: "Piece",
    grid: list,
    directions: tuple,
) -> list[tuple[int, int]]:

    moves: list[tuple[int, int]] = []
    r0, c0 = piece.position

    for dr, dc in directions:
        r, c = r0 + dr, c0 + dc
        blocked = False

        while inBounds(r, c) and not blocked:
            occupant = grid[r][c]

            if occupant is None:
                moves.append((r, c))
                r += dr
                c += dc

            elif occupant.color != piece.color:
                moves.append((r, c))
                blocked = True

            else:
                blocked = True

    return moves

# All pieces inherit from Piece. It stores color, position, and a hasMoved flag.
# Key properties are class name, Unicode symbol, and opponent.
# Each subclass must implement getPseudoLegalMoves().
# copy() is used when cloning the board for move simulation.

class Piece:
    def __init__(self, color: str, position: tuple[int, int]) -> None:
        self.color: str = color
        self.position: tuple[int, int] = position
        self.hasMoved: bool = False

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def symbol(self) -> str:
        return UNICODE_PIECES[(self.color, self.name)]

    @property
    def opponent(self) -> str:
        return "black" if self.color == "white" else "white"

    def getPseudoLegalMoves(
        self,
        grid: list,
        enPassantTarget: Optional[tuple[int, int]] = None,
    ) -> list[tuple[int, int]]:
        raise NotImplementedError(
            f"{self.name}.getPseudoLegalMoves() must be implemented.")

    def copy(self) -> "Piece":
        clone = self.__class__(self.color, self.position)
        clone.hasMoved = self.hasMoved
        return clone

# Pawn handles forward movement, double advance from starting row,
# diagonal captures, en passant captures, and exposes attackSquares()
# separately (used by attack-detection logic).

class Pawn(Piece):
    @property
    def direction(self) -> int:
        return -1 if self.color == "white" else 1

    @property
    def startRow(self) -> int:
        return 6 if self.color == "white" else 1

    @property
    def promotionRow(self) -> int:
        return 0 if self.color == "white" else 7

    def getPseudoLegalMoves(
        self,
        grid: list,
        enPassantTarget: Optional[tuple[int, int]] = None,
    ) -> list[tuple[int, int]]:
        moves: list[tuple[int, int]] = []
        row, col = self.position
        dr = self.direction

        fwd1 = (row + dr, col)
        if inBounds(*fwd1) and grid[fwd1[0]][fwd1[1]] is None:
            moves.append(fwd1)

            if row == self.startRow:
                fwd2 = (row + 2 * dr, col)
                if grid[fwd2[0]][fwd2[1]] is None:
                    moves.append(fwd2)

        for dc in (-1, 1):
            diag = (row + dr, col + dc)
            if not inBounds(*diag):
                continue

            occupant = grid[diag[0]][diag[1]]
            isEnemyCapture = occupant is not None and occupant.color == self.opponent
            isEnPassant = diag == enPassantTarget

            if isEnemyCapture or isEnPassant:
                moves.append(diag)

        return moves

    def attackSquares(self) -> list[tuple[int, int]]:
        row, col = self.position
        dr = self.direction
        return [
            (row + dr, col + dc)
            for dc in (-1, 1)
            if inBounds(row + dr, col + dc)
        ]

# Knight uses a fixed list of 8 jump offsets.

class Knight(Piece):

    _OFFSETS: tuple = (
        (-2, -1), (-2, +1),
        (-1, -2), (-1, +2),
        (+1, -2), (+1, +2),
        (+2, -1), (+2, +1),
    )

    def getPseudoLegalMoves(
        self,
        grid: list,
        enPassantTarget: Optional[tuple[int, int]] = None,
    ) -> list[tuple[int, int]]:
        row, col = self.position
        return [
            (row + dr, col + dc)
            for dr, dc in self._OFFSETS
            if inBounds(row + dr, col + dc)
            and (
                grid[row + dr][col + dc] is None
                or grid[row + dr][col + dc].color == self.opponent)
        ]

# Bishop uses slidingMoves() with diagonal directions.

class Bishop(Piece):
    _DIRS: tuple = ((-1, -1), (-1, +1), (+1, -1), (+1, +1))

    def getPseudoLegalMoves(
        self,
        grid: list,
        enPassantTarget: Optional[tuple[int, int]] = None,
    ) -> list[tuple[int, int]]:
        return slidingMoves(self, grid, self._DIRS)

# Rook uses slidingMoves(), moving only at right angles

class Rook(Piece):
    _DIRS: tuple = ((-1, 0), (+1, 0), (0, -1), (0, +1))

    def getPseudoLegalMoves(
        self,
        grid: list,
        enPassantTarget: Optional[tuple[int, int]] = None,
    ) -> list[tuple[int, int]]:
        return slidingMoves(self, grid, self._DIRS)

# Queen uses slidingMoves() with all 8 directions.

class Queen(Piece):
    _DIRS: tuple = (
        (-1, -1), (-1, +1), (+1, -1), (+1, +1),
        (-1,  0), (+1,  0), ( 0, -1), ( 0, +1),
    )

    def getPseudoLegalMoves(
        self,
        grid: list,
        enPassantTarget: Optional[tuple[int, int]] = None,
    ) -> list[tuple[int, int]]:
        return slidingMoves(self, grid, self._DIRS)

# King uses a fixed list of 8 adjacent offsets. Castling is handled separately in GameState.

class King(Piece):
    _OFFSETS: tuple = (
        (-1, -1), (-1,  0), (-1, +1),
        ( 0, -1),           ( 0, +1),
        (+1, -1), (+1,  0), (+1, +1),
    )

    def getPseudoLegalMoves(
        self,
        grid: list,
        enPassantTarget: Optional[tuple[int, int]] = None,
    ) -> list[tuple[int, int]]:
        row, col = self.position
        return [
            (row + dr, col + dc)
            for dr, dc in self._OFFSETS
            if inBounds(row + dr, col + dc)
            and (
                grid[row + dr][col + dc] is None
                or grid[row + dr][col + dc].color == self.opponent)]

PROMOTABLE_PIECES = {
    "Queen": Queen,
    "Rook": Rook,
    "Bishop": Bishop,
    "Knight": Knight,
}

# Factory function that changes the pawn to the correct piece class upon promotion.
# It copies its color and position.

def createPromotedPiece(pawn: Pawn, choice: str) -> Piece:
    cls = PROMOTABLE_PIECES.get(choice)
    if cls is None:
        raise ValueError(
            f"'{choice}' is not a valid promotion choice. "
            f"Choose from: {', '.join(PROMOTABLE_PIECES)}.")
    promoted = cls(pawn.color, pawn.position)
    promoted.hasMoved = True
    return promoted
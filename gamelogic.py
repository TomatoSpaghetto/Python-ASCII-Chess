"""
gamelogic.py

Handles the game state and chess rules.
"""

from __future__ import annotations
from typing import Optional

from pieces import (
    Piece, Pawn, King, Rook, Knight, Bishop, Queen,
    createPromotedPiece,
)

# notationToPos converts algebraic notation into a (row, col) grid tuple.

def notationToPos(notation: str) -> Optional[tuple[int, int]]:
    s = notation.strip().upper()
    if len(s) != 2:
        return None
    fileChar, rankChar = s[0], s[1]
    if fileChar not in "ABCDEFGH" or rankChar not in "12345678":
        return None
    return 8 - int(rankChar), ord(fileChar) - ord("A")

# posToNotation is the reverse conversion, back to a string.

def posToNotation(row: int, col: int) -> str:
    return chr(ord("A") + col) + str(8 - row)

# findKing scans the board to locate the king of the given color.

def findKing(grid: list, color: str) -> Optional[tuple[int, int]]:
    for r in range(8):
        for c in range(8):
            piece = grid[r][c]
            if isinstance(piece, King) and piece.color == color:
                return r, c
    return None

# squareAttacked scans all pieces of byColor and checks whether any of them can reach the given square.
# Used for check detection and castling safety.

def squareAttacked(
    grid: list,
    row: int,
    col: int,
    byColor: str,
) -> bool:

    for r in range(8):
        for c in range(8):
            piece = grid[r][c]
            if piece is None or piece.color != byColor:
                continue

            if isinstance(piece, Pawn):
                threatened = piece.attackSquares()
            else:
                threatened = piece.getPseudoLegalMoves(grid)

            if (row, col) in threatened:
                return True

    return False

# kingInCheck finds the king, then calls squareAttacked to determine if it's currently in check.

def kingInCheck(grid: list, color: str) -> bool:
    kingPos = findKing(grid, color)
    if kingPos is None:
        return False
    opponent = "black" if color == "white" else "white"
    return squareAttacked(grid, kingPos[0], kingPos[1], opponent)

# simulateMove returns a shallow copy of the board with the move applied
# Used to test whether a move leaves the king in check without altering the real game state.

def simulateMove(
    grid: list,
    piece: Piece,
    target: tuple[int, int],
    enPassantTarget: Optional[tuple[int, int]],
) -> list:
    newGrid = [row[:] for row in grid]
    fr, fc = piece.position
    tr, tc = target

    if isinstance(piece, Pawn) and enPassantTarget == target:
        newGrid[fr][tc] = None

    newGrid[tr][tc] = newGrid[fr][fc]
    newGrid[fr][fc] = None

    return newGrid

# GameState is the class that controls the game state (duh) - the 8×8 grid, whose turn it is,
# the en passant target square, castling rights for both sides, and the move history.

class GameState:

# __init__ Runs automatically when you create a new GameState. It sets up all starting values:
# The grid is an 8x8 board. By using Optional, it's saying that each cell on the board can either hold a Piece object or use None as an empty space.
# currentTurn Starts as "white" since white always goes first.
# enPassantTarget starts as None, gets set whenever a pawn double-advances so the next move can check for en passant captures.
# castlingRights tracks whether each side still has kingside/queenside castling available. Starts all True and gets set to false as kings and rooks move.
# history is an empty stack of lists. The board positions get pushed here before each move to support the takeback feature.
# Finally, __init__ calls setupBoard to place all pieces in their starting positions.

    def __init__(self) -> None:
        self.grid: list[list[Optional[Piece]]] = [
            [None] * 8 for _ in range(8)]
        self.currentTurn: str = "white"
        self.enPassantTarget: Optional[tuple[int, int]] = None
        self.castlingRights: dict = {
            "white": {"kingside": True, "queenside": True},
            "black": {"kingside": True, "queenside": True},
        }
        self.history: list[dict] = []
        self.setupBoard()

# setupBoard places all pieces on the board in their starting positions.

    def setupBoard(self) -> None:
        backRank = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        for col, PieceClass in enumerate(backRank):
            self.grid[0][col] = PieceClass("black", (0, col))
            self.grid[7][col] = PieceClass("white", (7, col))
        for col in range(8):
            self.grid[1][col] = Pawn("black", (1, col))
            self.grid[6][col] = Pawn("white", (6, col))

# isInCheck returns True if the given color's king is currently in check.

    def isInCheck(self, color: Optional[str] = None) -> bool:
        return kingInCheck(self.grid, color or self.currentTurn)

# legalMovesFor gets pseudo-legal moves from the piece, adds castling moves if it's a king,
# then filters out any move that would leave the player's own king in check.

    def legalMovesFor(self, piece: Piece) -> list[tuple[int, int]]:
        pseudo = piece.getPseudoLegalMoves(
            self.grid, self.enPassantTarget)
        if isinstance(piece, King):
            pseudo = pseudo + self.castlingMoves(piece)

        return [sq for sq in pseudo if not self.leavesInCheck(piece, sq)]

# allLegalMoves collects every legal move for all pieces of the given color.
# Mostly used to detect checkmate and stalemate.

    def allLegalMoves(self, color: str) -> list[tuple["Piece", list]]:
        result = []
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p is not None and p.color == color:
                    moves = self.legalMovesFor(p)
                    if moves:
                        result.append((p, moves))
        return result

# returns 'checkmate', 'stalemate', 'check', or 'normal' for the given color
# by combining the results of allLegalMoves and kingInCheck.

    def gameStatus(self, color: Optional[str] = None) -> str:
        c = color or self.currentTurn
        hasMoves = bool(self.allLegalMoves(c))
        inCheck = kingInCheck(self.grid, c)

        if not hasMoves:
            return "checkmate" if inCheck else "stalemate"
        return "check" if inCheck else "normal"

# applyMove commits a move to the board. Handles en passant capture, castling rook relocation,
# castling rights revocation, and position/hasMoved updates. Returns True if pawn promotion is needed.

    def applyMove(self, piece: Piece, target: tuple[int, int]) -> bool:
        self.pushHistory()

        fr, fc = piece.position
        tr, tc = target

        isEnPassant = isinstance(piece, Pawn) and self.enPassantTarget == target
        isCastling = isinstance(piece, King) and abs(tc - fc) == 2

        self.enPassantTarget = (
            ((fr + tr) // 2, tc)
            if isinstance(piece, Pawn) and abs(tr - fr) == 2
            else None)

        if isEnPassant:
            self.grid[fr][tc] = None

        if isCastling:
            self.relocateCastlingRook(fr, tc)

        self.revokeCastlingRights(piece, fc)

        self.grid[tr][tc] = piece
        self.grid[fr][fc] = None
        piece.position = (tr, tc)
        piece.hasMoved = True

        if isinstance(piece, Pawn) and tr == piece.promotionRow:
            return True

        self.switchTurn()
        return False

# applyPromotion replaces the pawn on the board with the promoted piece and switches the turn.

    def applyPromotion(self, pawn: Pawn, choice: str) -> None:
        promoted = createPromotedPiece(pawn, choice)
        r, c = pawn.position
        self.grid[r][c] = promoted
        self.switchTurn()

# takeback returns True or False depending on whether the takeback succeeded.
# If the history stack is empty, there's nothing to undo, so it returns False immediately.
# self.history.pop (<- Fun built-in function that I learned during this project) removes and returns the most recent snapshot from the history stack.
# self.grid, self.enPassantTarget, self.currentTurn, and self.castlingRights
# are all overwritten with the saved snapshot values, winding the game back one move.

    def takeback(self) -> bool:
        if not self.history:
            return False
        saved = self.history.pop()
        self.grid = saved["grid"]
        self.enPassantTarget = saved["enPassantTarget"]
        self.currentTurn = saved["currentTurn"]
        self.castlingRights = saved["castlingRights"]
        return True

    def switchTurn(self) -> None:
        self.currentTurn = "black" if self.currentTurn == "white" else "white"

# pushHistory copies the full board state (including piece objects) onto the history stack before each move.

    def pushHistory(self) -> None:
        self.history.append({
            "grid":              self.cloneGrid(),
            "enPassantTarget":   self.enPassantTarget,
            "currentTurn":       self.currentTurn,
            "castlingRights": {
                "white": dict(self.castlingRights["white"]),
                "black": dict(self.castlingRights["black"]),
            },
        })

# cloneGrid returns a copy of the board grid, which is used to support the takeback function.

    def cloneGrid(self) -> list:
        return [
            [p.copy() if p is not None else None for p in row]
            for row in self.grid]

# leavesInCheck Tests whether a given move would leave the current player's own king in check.

    def leavesInCheck(self, piece: Piece, target: tuple[int, int]) -> bool:
        simulated = simulateMove(
            self.grid, piece, target, self.enPassantTarget)
        return kingInCheck(simulated, piece.color)

#castlingMoves checks castling rights, board clearance, and passage safety (squares the king passes through can't be attacked),
# and then returns valid castling moves.

    def castlingMoves(self, king: King) -> list[tuple[int, int]]:
        if king.hasMoved or kingInCheck(self.grid, king.color):
            return []

        row = king.position[0]
        opp = king.opponent
        rights = self.castlingRights[king.color]
        moves: list[tuple[int, int]] = []

        if rights["kingside"]:
            rook = self.grid[row][7]
            squaresClear = (
                self.grid[row][5] is None and
                self.grid[row][6] is None)
            passageSafe = (
                not squareAttacked(self.grid, row, 5, opp) and
                not squareAttacked(self.grid, row, 6, opp))
            if (isinstance(rook, Rook) and not rook.hasMoved
                    and squaresClear and passageSafe):
                moves.append((row, 6))

        if rights["queenside"]:
            rook = self.grid[row][0]
            squaresClear = (
                self.grid[row][1] is None and
                self.grid[row][2] is None and
                self.grid[row][3] is None)
            passageSafe = (
                not squareAttacked(self.grid, row, 3, opp) and
                not squareAttacked(self.grid, row, 2, opp))
            if (isinstance(rook, Rook) and not rook.hasMoved
                    and squaresClear and passageSafe):
                moves.append((row, 2))

        return moves

# relocateCastlingRook moves the appropriate rook to its new position.

    def relocateCastlingRook(
        self, kingRow: int, kingDestCol: int) -> None:
        if kingDestCol == 6:
            rook = self.grid[kingRow][7]
            self.grid[kingRow][5] = rook
            self.grid[kingRow][7] = None
            rook.position = (kingRow, 5)
            rook.hasMoved = True
        else:
            rook = self.grid[kingRow][0]
            self.grid[kingRow][3] = rook
            self.grid[kingRow][0] = None
            rook.position = (kingRow, 3)
            rook.hasMoved = True

# revokeCastlingRights removes castling rights when a king or rook moves from its starting square.

    def revokeCastlingRights(
        self, piece: Piece, fromCol: int) -> None:
        if isinstance(piece, King):
            self.castlingRights[piece.color]["kingside"] = False
            self.castlingRights[piece.color]["queenside"] = False
        elif isinstance(piece, Rook):
            if fromCol == 0:
                self.castlingRights[piece.color]["queenside"] = False
            elif fromCol == 7:
                self.castlingRights[piece.color]["kingside"] = False
import pygame, random, os
import numpy as np


class TetrisGame:
    def __init__(self, GameSize: tuple = (10, 15), BlockSize=30, CustomPieces=None):
        """Initializes the game with the specified size and custom pieces.

        Args:
            GameSize (tuple): The size of the game matrix (width, height). (default=(10, 15))
            BlockSize (int): The size of each block in pixels. (default=30)
            CustomPieces (dict): A dictionary of custom pieces to use in the game. (default=standard pieces)
        """
        self.GameMatrixSize = GameSize
        self.GameMatrix = [[0 for x in range(self.GameMatrixSize[0])] for y in range(self.GameMatrixSize[1])]

        self.BLOCK_SIZE = BlockSize
        self.WINDOW_WIDTH = self.GameMatrixSize[0] * self.BLOCK_SIZE
        self.WINDOW_HEIGHT = self.GameMatrixSize[1] * self.BLOCK_SIZE

        #check if the windows size is greater than the screen size
        if self.WINDOW_WIDTH > 1920 or self.WINDOW_HEIGHT > 1080:
            # Warn the user
            print(f"\033[91m\n! WARNING !\nThe window size generated is greater than 1920w or 1080h ({self.WINDOW_WIDTH} x {self.WINDOW_HEIGHT}), press enter to continue\033[0m")
            input()
        

        if not CustomPieces:
            self.Pieces = {
                "I": np.array([
                    [0, 0, 0, 0],
                    [0, 0, 0, 0],
                    [1, 1, 1, 1],
                    [0, 0, 0, 0]
                    ]),

                "square": np.array([
                    [1, 1],
                    [1, 1]
                    ]),

                "T": np.array([
                    [0, 0, 0],
                    [1, 1, 1],
                    [0, 1, 0]
                    ]),

                "L": np.array([
                    [0, 0, 0],
                    [1, 1, 1],
                    [1, 0, 0]
                    ]),

                "J": np.array([
                    [0, 0, 0],
                    [1, 1, 1],
                    [0, 0, 1]
                    ]),

                "S": np.array([
                    [0, 0, 0],
                    [0, 1, 1],
                    [1, 1, 0]
                    ]),

                "Z": np.array([
                    [0, 0, 0],
                    [1, 1, 0],
                    [0, 1, 1]
                    ])
            }
        else:
            self.Pieces = CustomPieces


        self.PIECE_COLORS = [
            (205, 133, 63),   # Peru (Cardboard Brown)
            (139, 69, 19),    # Saddle Brown (Heavy Package)
            (222, 184, 135),  # Burly Wood (Light Cardboard)
            (160, 82, 45),    # Sienna (Wooden Crates)
            (244, 164, 96),   # Sandy Brown (Packing Paper)
            (210, 180, 140),  # Tan (Standard Package)
            (112, 128, 144)   # Slate Gray (Metal or Plastic Packages)
        ]

        self.PIECE_OUTLINE = 0.3
        self.GAME_COLOR = (169, 169, 169)
        self.LimitLine = 2

    def InitializeGameMatrix(self):
        """Resets the game matrix to the initial state."""
        self.GameMatrix = [[0 for x in range(self.GameMatrixSize[0])] for y in range(self.GameMatrixSize[1])]

    def DrawGameMatrix(self, screen: pygame.Surface, pieces: list):
        """Draws the game matrix and the pieces on the provided screen surface.
        
        Args:
            screen (pygame.Surface): The surface to draw on.
            pieces (list): The list of current pieces to draw.
        """
        pygame.draw.line(screen,
                         (255, 105, 97),
                         (0, self.LimitLine * self.BLOCK_SIZE),
                         (self.WINDOW_WIDTH, self.LimitLine * self.BLOCK_SIZE),
                         2)

        for piece in pieces:
            piece.DrawPiece(screen)

    def PlacePiece(self, piece):
        """Places a piece in the game matrix at its current position.
        
        Args:
            piece: The piece to be placed.
        """
        for i in range(piece.shape.shape[0]):
            for j in range(piece.shape.shape[1]):
                if piece.shape[i][j] == 1:
                    if 0 <= piece.y + i < self.GameMatrixSize[1] and 0 <= piece.x + j < self.GameMatrixSize[0]:
                        self.GameMatrix[piece.y + i][piece.x + j] = 1

    def ClearPiece(self, piece):
        """Clears a piece from the game matrix.

        
        used when moving or rotating a piece to clear its previous position.
        
        Args:
            piece: The piece to be cleared.
        """
        for i in range(piece.shape.shape[0]):
            for j in range(piece.shape.shape[1]):
                if piece.shape[i][j] == 1:
                    if 0 <= piece.y + i < self.GameMatrixSize[1] and 0 <= piece.x + j < self.GameMatrixSize[0]:
                        self.GameMatrix[piece.y + i][piece.x + j] = 0

    def CanMove(self, piece, direction):
        """Checks if a piece can move in the specified direction.
        
        Args:
            piece: The piece to check.
            direction (str): The direction to check ('left', 'right', 'down').

        Returns:
            bool: True if the piece can move, False otherwise.
        """
        self.ClearPiece(piece)
        CanMove = True
        for i in range(piece.shape.shape[0]):
            for j in range(piece.shape.shape[1]):
                if piece.shape[i][j] == 1:
                    new_x = piece.x + j
                    new_y = piece.y + i
                    if direction == "left":
                        new_x -= 1
                    elif direction == "right":
                        new_x += 1
                    elif direction == "down":
                        new_y += 1
                    if new_x < 0 or new_x >= self.GameMatrixSize[0] or new_y >= self.GameMatrixSize[1] or self.GameMatrix[new_y][new_x] == 1:
                        CanMove = False
                        break

            if not CanMove:
                break

        self.PlacePiece(piece)
        return CanMove

    def MovePiece(self, piece, direction):
        """Moves a piece in the specified direction if possible.
        
        Args:
            piece: The piece to move.
            direction (str): The direction to move the piece ('left', 'right', 'down').

        Returns:
            bool: True if the piece was moved, False otherwise.
        """
        if self.CanMove(piece, direction):
            self.ClearPiece(piece)
            if direction == "left":
                piece.x -= 1
            elif direction == "right":
                piece.x += 1
            elif direction == "down":
                piece.y += 1
            self.PlacePiece(piece)
            return True
        return False

    def CanRotate(self, piece):
        """Checks if a piece can be rotated without colliding.
        
        Args:
            piece: The piece to check.

        Returns:
            bool: True if the piece can rotate, False otherwise.
        """
        self.ClearPiece(piece)
        CanRotate = True
        new_shape = np.rot90(piece.shape)
        for i in range(new_shape.shape[0]):
            for j in range(new_shape.shape[1]):
                if new_shape[i][j] == 1:
                    new_x = piece.x + j
                    new_y = piece.y + i
                    if new_x < 0 or new_x >= self.GameMatrixSize[0] or new_y >= self.GameMatrixSize[1] or self.GameMatrix[new_y][new_x] == 1:
                        CanRotate = False
                        break

            if not CanRotate:
                break

        self.PlacePiece(piece)
        return CanRotate

    def CanSpawnNewPiece(self):
        """Checks if a new piece can be spawned in the game matrix.
        
        Returns:
            bool: True if a new piece can be spawned, False otherwise.
        """
        for x in range(self.GameMatrixSize[0]):
            if self.GameMatrix[self.LimitLine][x] == 1:
                return False
        return True

    def SpawnNewPiece(self):
        """Spawns a new piece randomly from the available shapes.
        
        Returns:
            Piece: The newly spawned piece, or None if no new piece can be spawned.
        """
        if self.CanSpawnNewPiece():
            shape = random.choice(list(self.Pieces.keys()))
            return Piece(int((self.GameMatrixSize[0]-2)/2), 0, shape, self)
        else:
            return None

    def GameLoop(self):
        """Runs the main game loop, handling events and updating the game state."""
        pygame.init()
        Screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        Clock = pygame.time.Clock()
        self.InitializeGameMatrix()
        CurrentPiece = self.SpawnNewPiece()

        Pieces = [CurrentPiece]

        Running = True
        MoveDownTimer = 0
        MoveDownInterval = 500  # milliseconds

        while Running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    Running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.MovePiece(CurrentPiece, "left")
                    elif event.key == pygame.K_RIGHT:
                        self.MovePiece(CurrentPiece, "right")
                    elif event.key == pygame.K_DOWN:
                        self.MovePiece(CurrentPiece, "down")
                    elif event.key == pygame.K_UP:
                        if self.CanRotate(CurrentPiece):
                            self.ClearPiece(CurrentPiece)
                            CurrentPiece.rotate()
                            self.PlacePiece(CurrentPiece)

            Screen.fill(self.GAME_COLOR)
            self.DrawGameMatrix(Screen, Pieces)
            pygame.display.flip()
            Clock.tick(60)  # Run the game loop at 60 frames per second

            PiecesText = [piece.type for piece in Pieces]

            MoveDownTimer += Clock.get_time()
            if MoveDownTimer >= MoveDownInterval:
                MoveDownTimer = 0
                if not self.MovePiece(CurrentPiece, "down"):
                    CurrentPiece = self.SpawnNewPiece()
                    if CurrentPiece is None:
                        Running = False

                    Pieces.append(CurrentPiece)

        pygame.quit()
        return PiecesText


class Piece:
    def __init__(self, x:int, y:int, shape:str, game:TetrisGame):
        """Initializes a piece with its position, shape, color, and associated game.
        
        Args:
            x (int): The x-coordinate of the piece.
            y (int): The y-coordinate of the piece.
            shape (str): The type of shape for the piece.
            game (TetrisGame): The game instance associated with this piece.
        """
        self.x = x
        self.y = y
        self.type = shape
        self.shape = game.Pieces[shape]
        self.color = random.choice(game.PIECE_COLORS)
        self.game = game

    def rotate(self):
        """Rotates the piece clockwise by 90 degrees."""
        self.shape = np.rot90(self.shape, -1)

    def DrawPiece(self, screen: pygame.Surface):
        """Draws the piece on the provided screen surface.
        
        Args:
            screen (pygame.Surface): The surface to draw the piece on.
        """
        for i in range(self.shape.shape[0]):
            for j in range(self.shape.shape[1]):
                if self.shape[i][j] == 1:
                    pygame.draw.rect(screen,
                                     self.color,
                                     pygame.Rect(
                                         (self.x + j) * self.game.BLOCK_SIZE,
                                         (self.y + i) * self.game.BLOCK_SIZE,
                                         self.game.BLOCK_SIZE,
                                         self.game.BLOCK_SIZE
                                         )
                                     )

                    pygame.draw.rect(screen,
                                     tuple(int(c * self.game.PIECE_OUTLINE) for c in self.color),
                                     pygame.Rect(
                                         (self.x + j) * self.game.BLOCK_SIZE,
                                         (self.y + i) * self.game.BLOCK_SIZE,
                                         self.game.BLOCK_SIZE,
                                         self.game.BLOCK_SIZE
                                         ),
                                     2)

if __name__ == "__main__":
    game = TetrisGame(GameSize=(40, 30))
    print(game.GameLoop())

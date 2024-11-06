import pygame, random, os
import numpy as np


class TetrisGame:
    def __init__(self, GameSize: tuple = (10, 15), BlockSize=30, CustomPieces=None, UseSprites=False):
        """Initializes the game with the specified size and custom pieces.

        Args:
            GameSize (tuple): The size of the game matrix (width, height). (default=(10, 15))
            BlockSize (int): The size of each block in pixels. (default=30)
            CustomPieces (dict): A dictionary of custom pieces to use in the game. (default=standard pieces)
            UseSprites (bool): Flag to determine if sprites in sprites folder should be used ({PieceType}.png). (default=False)
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

        self.UseSprites = UseSprites


    def LoadSprites(self) -> dict:
        """Loads sprites for each piece type.

        Returns:
            dict: A dictionary mapping piece types to their sprite images.
        """
        Sprites = {}
        SpritesDir = "sprites"  # Ensure this directory exists with sprite images
        for PieceType in self.Pieces.keys():
            SpritePath = os.path.join(SpritesDir, f"{PieceType}.png")
            if os.path.exists(SpritePath):
                Sprite = pygame.image.load(SpritePath).convert_alpha()
                PieceWidth, PieceHeight = self.Pieces[PieceType].shape[1] * self.BLOCK_SIZE, self.Pieces[PieceType].shape[0] * self.BLOCK_SIZE
                Sprite = pygame.transform.scale(Sprite, (PieceWidth, PieceHeight))
                Sprites[PieceType] = Sprite
            else:
                Sprites[PieceType] = None  # Fallback if sprite not found
        return Sprites

    def InitializeGameMatrix(self):
        """Resets the game matrix to the initial state."""
        self.GameMatrix = [[0 for x in range(self.GameMatrixSize[0])] for y in range(self.GameMatrixSize[1])]

    def DrawGameMatrix(self, screen: pygame.Surface, Pieces: list):
        """Draws the game matrix and the pieces on the provided screen surface.
        
        Args:
            screen (pygame.Surface): The surface to draw on.
            Pieces (list): The list of current pieces to draw.
        """
        pygame.draw.line(screen,
                         (255, 105, 97),
                         (0, self.LimitLine * self.BLOCK_SIZE),
                         (self.WINDOW_WIDTH, self.LimitLine * self.BLOCK_SIZE),
                         2)

        for piece in Pieces:
            piece.DrawPiece(screen)

    def PlacePiece(self, Piece):
        """Places a piece in the game matrix at its current position.
        
        Args:
            Piece: The piece to be placed.
        """
        for i in range(Piece.Shape.shape[0]):
            for j in range(Piece.Shape.shape[1]):
                if Piece.Shape[i][j] == 1:
                    if 0 <= Piece.y + i < self.GameMatrixSize[1] and 0 <= Piece.x + j < self.GameMatrixSize[0]:
                        self.GameMatrix[Piece.y + i][Piece.x + j] = 1

    def ClearPiece(self, Piece):
        """Clears a piece from the game matrix.

        
        used when moving or rotating a piece to clear its previous position.
        
        Args:
            Piece: The piece to be cleared.
        """
        for i in range(Piece.Shape.shape[0]):
            for j in range(Piece.Shape.shape[1]):
                if Piece.Shape[i][j] == 1:
                    if 0 <= Piece.y + i < self.GameMatrixSize[1] and 0 <= Piece.x + j < self.GameMatrixSize[0]:
                        self.GameMatrix[Piece.y + i][Piece.x + j] = 0

    def CanMove(self, Piece, Direction):
        """Checks if a piece can move in the specified direction.
        
        Args:
            Piece: The piece to check.
            Direction (str): The direction to check ('left', 'right', 'down').

        Returns:
            bool: True if the piece can move, False otherwise.
        """
        self.ClearPiece(Piece)
        CanMove = True
        for i in range(Piece.Shape.shape[0]):
            for j in range(Piece.Shape.shape[1]):
                if Piece.Shape[i][j] == 1:
                    NewX = Piece.x + j
                    NewY = Piece.y + i
                    if Direction == "left":
                        NewX -= 1
                    elif Direction == "right":
                        NewX += 1
                    elif Direction == "down":
                        NewY += 1
                    if NewX < 0 or NewX >= self.GameMatrixSize[0] or NewY >= self.GameMatrixSize[1] or self.GameMatrix[NewY][NewX] == 1:
                        CanMove = False
                        break

            if not CanMove:
                break

        self.PlacePiece(Piece)
        return CanMove

    def MovePiece(self, Piece, Direction):
        """Moves a piece in the specified direction if possible.
        
        Args:
            Piece: The piece to move.
            Direction (str): The direction to move the piece ('left', 'right', 'down').

        Returns:
            bool: True if the piece was moved, False otherwise.
        """
        if self.CanMove(Piece, Direction):
            self.ClearPiece(Piece)
            if Direction == "left":
                Piece.x -= 1
            elif Direction == "right":
                Piece.x += 1
            elif Direction == "down":
                Piece.y += 1
            self.PlacePiece(Piece)
            return True
        return False

    def CanRotate(self, Piece):
        """Checks if a piece can be rotated without colliding.
        
        Args:
            Piece: The piece to check.

        Returns:
            bool: True if the piece can rotate, False otherwise.
        """
        self.ClearPiece(Piece)
        CanRotate = True
        NewShape = np.rot90(Piece.Shape)
        for i in range(NewShape.shape[0]):
            for j in range(NewShape.shape[1]):
                if NewShape[i][j] == 1:
                    NewX = Piece.x + j
                    NewY = Piece.y + i
                    if NewX < 0 or NewX >= self.GameMatrixSize[0] or NewY >= self.GameMatrixSize[1] or self.GameMatrix[NewY][NewX] == 1:
                        CanRotate = False
                        break

            if not CanRotate:
                break

        self.PlacePiece(Piece)
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
        self.PieceSprites = self.LoadSprites() if self.UseSprites else {}
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
                            CurrentPiece.Rotate()
                            self.PlacePiece(CurrentPiece)

            Screen.fill(self.GAME_COLOR)
            self.DrawGameMatrix(Screen, Pieces)
            pygame.display.flip()
            Clock.tick(60)  # Run the game loop at 60 frames per second

            PiecesText = [piece.Type for piece in Pieces]

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
    def __init__(self, x: int, y: int, Shape: str, Game: TetrisGame):
        """Initializes a piece with its position, shape, color, and associated game.
        
        Args:
            x (int): The x-coordinate of the piece.
            y (int): The y-coordinate of the piece.
            Shape (str): The type of shape for the piece.
            Game (TetrisGame): The game instance associated with this piece.
        """
        self.x = x
        self.y = y
        self.Type = Shape
        self.Shape = Game.Pieces[Shape]
        self.Color = random.choice(Game.PIECE_COLORS)
        self.Game = Game
        self.OriginalSprite = Game.PieceSprites.get(Shape, None)  # Store original sprite
        self.Sprite = self.OriginalSprite
        self.RotationAngle = 0  # Track the rotation angle

    def Rotate(self):
        """Rotates the piece clockwise by 90 degrees and rotates the sprite if available."""
        self.Shape = np.rot90(self.Shape, -1)  # Rotate shape 90 degrees clockwise

        if self.OriginalSprite:
            # Update rotation angle
            self.RotationAngle = (self.RotationAngle + 90) % 360
            # Rotate sprite based on the total rotation angle
            self.Sprite = pygame.transform.rotate(self.OriginalSprite, -self.RotationAngle)

    def DrawPiece(self, screen: pygame.Surface):
        """Draws the piece on the provided screen surface.

        Args:
            screen (pygame.Surface): The surface to draw the piece on.
        """
        if self.Sprite:
            # Calculate the width and height of the piece
            width, height = self.Shape.shape[1] * self.Game.BLOCK_SIZE, self.Shape.shape[0] * self.Game.BLOCK_SIZE
            # Draw the rotated sprite
            screen.blit(self.Sprite, (self.x * self.Game.BLOCK_SIZE, self.y * self.Game.BLOCK_SIZE))
        else:
            # Draw each block of the piece
            for i in range(self.shape.shape[0]):
                for j in range(self.shape.shape[1]):
                    if self.shape[i][j] == 1:
                        block_x = (self.x + j) * self.game.BLOCK_SIZE
                        block_y = (self.y + i) * self.game.BLOCK_SIZE
                        pygame.draw.rect(screen,
                                         self.color,
                                         pygame.Rect(
                                             block_x,
                                             block_y,
                                             self.game.BLOCK_SIZE,
                                             self.game.BLOCK_SIZE
                                         ))
                        pygame.draw.rect(screen,
                                         tuple(int(c * self.game.PIECE_OUTLINE) for c in self.color),
                                         pygame.Rect(
                                             block_x,
                                             block_y,
                                             self.game.BLOCK_SIZE,
                                             self.game.BLOCK_SIZE
                                         ),
                                         2)


if __name__ == "__main__":
    CustomPieces = {
        "Package": np.array([
            [0, 0, 0, 0],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
            [0, 0, 0, 0]
        ]),
        "T": np.array([
            [0, 0, 0],
            [1, 1, 1],
            [0, 1, 0]
        ]),
    }
    
    game = TetrisGame(GameSize=(10, 20), CustomPieces=CustomPieces, UseSprites=True)
    print(game.GameLoop())

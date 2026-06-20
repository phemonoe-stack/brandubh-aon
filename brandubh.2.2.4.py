import pygame
import pygame_menu
import sys
import random

# ----------------------------- Brandubh V.3 (Audio Enhanced) -----------------------------

# --- Constants & Configuration ---
BOARD_SIZE = 7
CELL_SIZE = 70

# Padding offsets to align the grid within the window
PADDING_X = 55
PADDING_Y = 50

# Calculate window geometry based on padding and grid size
GRID_TOTAL = BOARD_SIZE * CELL_SIZE
WIDTH = GRID_TOTAL + (PADDING_X * 2)
HEIGHT = GRID_TOTAL + (PADDING_Y * 2)
FPS = 60

# Scale piece images should be rendered at
IMAGE_SIZE = (CELL_SIZE - 10, CELL_SIZE - 10)

# Red highlight with sufficient alpha for BLEND_RGBA_MAX blending
COLOR_HIGHLIGHT = (245, 0, 0, 128)

# --- Game State Setup ---
# Board encoding: 0 = empty, 1 = attacker, 2 = defender, 3 = king
STARTING_BOARD = [
    [0, 1, 1, 0, 1, 1, 0],
    [1, 0, 0, 2, 0, 0, 1],
    [1, 0, 0, 2, 0, 0, 1],
    [0, 2, 2, 3, 2, 2, 0],
    [1, 0, 0, 2, 0, 0, 1],
    [1, 0, 0, 2, 0, 0, 1],
    [0, 1, 1, 0, 1, 1, 0],
]

CORNERS = {(0, 0), (0, 6), (6, 0), (6, 6)}
THRONE = (3, 3)


class BrandubhGame:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Brandubh")

        try:
            icon_image = pygame.image.load("favicon.ico")
            pygame.display.set_icon(icon_image)
        except pygame.error as e:
            print(f"Warning: Could not load favicon.ico: {e}")

        self.clock = pygame.time.Clock()

        # --- AI Settings ---
        self.player_role = 1       # 1 = Attacker, 2 = Defender
        self.ai_player = 2         # Which side the AI controls
        self.ai_difficulty = "easy"

        # --- Load Sound Effects ---
        self.sounds = {}
        sound_files = {
            "start":   "game_start.wav",
            "move":    "piece_move.wav",
            "capture": "piece_capture.wav",
            "escape":  "king_escape.wav",
            "ending":  "game_end.wav",
        }
        for key, file in sound_files.items():
            try:
                self.sounds[key] = pygame.mixer.Sound(file)
            except pygame.error as e:
                print(f"Warning: Could not load sound '{file}': {e}")
                self.sounds[key] = None

        # --- Internal flag used to suppress sounds during AI simulation ---
        self._suppress_sound = False

        # Initialize game state variables
        self.reset_game()
        self.menu_enabled = True

        # Tracks the "Return to Main Menu" button rect for click detection
        self.game_over_btn_rect = pygame.Rect(0, 0, 0, 0)

        # Load board background image
        try:
            self.board_img = pygame.image.load("board.png").convert()
        except pygame.error:
            try:
                self.board_img = pygame.image.load("board.jpg").convert()
            except pygame.error as e:
                print(f"Error: Could not load board image: {e}")
                self.board_img = pygame.Surface((WIDTH, HEIGHT))
                self.board_img.fill((180, 140, 80))

        self.board_img = pygame.transform.scale(self.board_img, (WIDTH, HEIGHT))

        # Load and scale piece images
        try:
            attacker_img = pygame.image.load("attacker.png").convert_alpha()
            defender_img = pygame.image.load("defender.png").convert_alpha()
            king_img     = pygame.image.load("king.png").convert_alpha()
            self.images = {
                1: pygame.transform.smoothscale(attacker_img, IMAGE_SIZE),
                2: pygame.transform.smoothscale(defender_img, IMAGE_SIZE),
                3: pygame.transform.smoothscale(king_img,     IMAGE_SIZE),
            }
        except pygame.error as e:
            print(f"Error loading piece images: {e}")
            self.images = None

        # Load popup background image
        try:
            self.popup_bg_original = pygame.image.load("newconnaught_menu_sm1.png").convert_alpha()
        except pygame.error:
            self.popup_bg_original = None

        # Build the menu once
        self.menu = self.create_menu()
        self.play_sound("start")

    # ----------------------------- Game State -----------------------------

    def reset_game(self):
        self.board = [row[:] for row in STARTING_BOARD]
        self.turn = 1              # 1 = Attackers move first
        self.selected_piece = None
        self.valid_moves = []
        self.game_over = False
        self.winner = None
        if hasattr(self, "menu_enabled"):
            self.menu_enabled = False

    def play_sound(self, key, stop_first=False):
        """Play a sound by key name. Suppressed during AI simulation."""
        if self._suppress_sound:
            return
        sound = self.sounds.get(key)
        if sound:
            if stop_first:
                sound.stop()
            sound.play()

    # ----------------------------- Menu -----------------------------

    def set_player_role(self, selected_item, value):
        self.player_role = value
        self.ai_player = 2 if value == 1 else 1

    def set_difficulty(self, selected_item, value):
        self.ai_difficulty = value

    def create_menu(self):
        menu_bg_image = None
        try:
            menu_bg_image = pygame_menu.baseimage.BaseImage(
                image_path="newconnaught_menu.png",
                drawing_mode=pygame_menu.baseimage.IMAGE_MODE_FILL,
            )
        except Exception as e:
            print(f"Warning: Could not load menu background: {e}")

        my_theme = pygame_menu.themes.THEME_BLUE.copy()
        if menu_bg_image:
            my_theme.background_color = menu_bg_image

        my_theme.title_background_color   = (30, 20, 15)
        my_theme.title_font_color         = (245, 230, 200)
        my_theme.widget_font_color        = (0, 158, 96)
        my_theme.widget_font_shadow       = True
        my_theme.widget_font_shadow_color = (226, 188, 5)
        my_theme.selection_color          = (245, 136, 63)

        menu = pygame_menu.Menu(
            "Brandubh Menu", WIDTH // 1.5, HEIGHT // 1.5, theme=my_theme
        )
        menu.add.selector(
            "Play As: ",
            [("Attacker", 1), ("Defender", 2)],
            onchange=self.set_player_role,
        )
        menu.add.selector(
            "Difficulty: ",
            [("Easy", "easy"), ("Medium", "medium"), ("Hard", "hard")],
            onchange=self.set_difficulty,
        )
        menu.add.button("Play", self.start_match)
        menu.add.button("Restart Game", self.reset_game)
        menu.add.button("Quit", pygame_menu.events.EXIT)
        return menu

    def toggle_menu(self):
        self.menu_enabled = not self.menu_enabled
        if self.menu_enabled:
            self.play_sound("start", stop_first=True)

    def start_match(self):
        self.menu_enabled = False
        self.play_sound("start", stop_first=True)

    # ----------------------------- Movement Logic -----------------------------

    def get_valid_moves(self, row, col):
        piece = self.board[row][col]

        # Piece must belong to the current player
        if piece == 0:
            return []
        if piece == 1 and self.turn != 1:
            return []
        if piece in (2, 3) and self.turn != 2:
            return []

        moves = []
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        # Opponents are used to detect suicide (sandwiching) at the destination
        opponents = [2, 3] if piece == 1 else [1]

        for dr, dc in directions:
            r, c = row + dr, col + dc
            while 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                if self.board[r][c] != 0:
                    break  # Path blocked by another piece

                # Only the king may land on the throne or corners
                if (r, c) == THRONE or (r, c) in CORNERS:
                    if piece != 3:
                        r += dr
                        c += dc
                        continue

                # Prevent suicide moves: skip destinations where piece is immediately sandwiched
                sandwiched_h = (
                    0 <= c - 1 and c + 1 < BOARD_SIZE
                    and self.board[r][c - 1] in opponents
                    and self.board[r][c + 1] in opponents
                )
                sandwiched_v = (
                    0 <= r - 1 and r + 1 < BOARD_SIZE
                    and self.board[r - 1][c] in opponents
                    and self.board[r + 1][c] in opponents
                )
                if sandwiched_h or sandwiched_v:
                    r += dr
                    c += dc
                    continue

                moves.append((r, c))
                r += dr
                c += dc

        return moves

    def has_valid_moves(self, player_turn):
        """Return True if the given player has at least one legal move."""
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                piece = self.board[r][c]
                if player_turn == 1 and piece == 1:
                    if self.get_valid_moves(r, c):
                        return True
                elif player_turn == 2 and piece in (2, 3):
                    if self.get_valid_moves(r, c):
                        return True
        return False

    def move_piece(self, start, end):
        r1, c1 = start
        r2, c2 = end
        piece = self.board[r1][c1]

        self.board[r2][c2] = piece
        self.board[r1][c1] = 0

        # King reaches a corner — defenders win
        if piece == 3 and (r2, c2) in CORNERS:
            self.game_over = True
            self.winner = "Defenders Win (King Escaped)!"
            self.play_sound("escape")
            self.play_sound("ending")
            # Turn switch intentionally skipped; game is over
            return

        captured = self.check_captures(r2, c2)
        if not captured and not self.game_over:
            self.play_sound("move")

        # Advance turn only if the game is still running
        if not self.game_over:
            self.turn = 2 if self.turn == 1 else 1

    def check_captures(self, r, c):
        """Check and remove any pieces sandwiched by the piece that just moved to (r, c)."""
        piece = self.board[r][c]
        opponents   = [2, 3] if piece == 1 else [1]
        friendly    = [1]    if piece == 1 else [2, 3]
        directions  = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        captured_any = False

        for dr, dc in directions:
            if self.game_over:
                break

            vr, vc = r + dr,     c + dc
            hr, hc = r + 2 * dr, c + 2 * dc

            if not (0 <= vr < BOARD_SIZE and 0 <= vc < BOARD_SIZE):
                continue

            victim = self.board[vr][vc]
            if victim not in opponents:
                continue

            if victim == 3:
                # King requires special capture logic
                self.check_king_capture(vr, vc)
            else:
                if 0 <= hr < BOARD_SIZE and 0 <= hc < BOARD_SIZE:
                    hostile = self.board[hr][hc]
                    is_hostile = (
                        hostile in friendly
                        or (hr, hc) in CORNERS
                        or (hr, hc) == THRONE
                    )
                    if is_hostile:
                        self.board[vr][vc] = 0
                        self.play_sound("capture")
                        captured_any = True

        return captured_any

    def check_king_capture(self, kr, kc):
        """
        The king is captured when surrounded on all four orthogonal sides by
        attackers or the throne. Board edges do NOT count as hostile.
        """
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        surrounded_count = 0

        for dr, dc in directions:
            r, c = kr + dr, kc + dc
            if 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                if self.board[r][c] == 1 or (r, c) == THRONE:
                    surrounded_count += 1
            # Board edge does NOT count — king on an edge cannot be captured
            # from the missing side by the board boundary alone.

        if surrounded_count == 4:
            self.game_over = True
            self.winner = "Attackers Win (King Captured)!"
            self.play_sound("ending")

    # ----------------------------- AI -----------------------------

    def evaluate_board(self):
        if self.game_over:
            if self.winner and "Defenders Win" in self.winner:
                return  10000
            if self.winner and "Attackers Win" in self.winner:
                return -10000

        score    = 0
        king_pos = None

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                piece = self.board[r][c]
                if piece == 1:
                    score -= 10
                elif piece == 2:
                    score += 15
                elif piece == 3:
                    king_pos = (r, c)
                    score += 50

        if king_pos:
            kr, kc  = king_pos
            min_dist = min(abs(kr - cx) + abs(kc - cy) for cx, cy in CORNERS)
            score += (12 - min_dist) * 5

        return score

    def minimax(self, depth, alpha, beta, maximizing_player):
        if depth == 0 or self.game_over:
            return self.evaluate_board(), None

        sim_turn  = 2 if maximizing_player else 1
        all_moves = []

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                piece = self.board[r][c]
                if (sim_turn == 1 and piece == 1) or (sim_turn == 2 and piece in (2, 3)):
                    for move in self.get_valid_moves(r, c):
                        all_moves.append(((r, c), move))

        if not all_moves:
            return self.evaluate_board(), None

        best_move = None
        # Suppress sounds for the duration of the simulation
        self._suppress_sound = True

        try:
            if maximizing_player:
                max_eval = float("-inf")
                for start, end in all_moves:
                    saved = self._save_state()
                    self.move_piece(start, end)
                    evaluation, _ = self.minimax(depth - 1, alpha, beta, False)
                    self._restore_state(saved)

                    if evaluation > max_eval:
                        max_eval  = evaluation
                        best_move = (start, end)
                    alpha = max(alpha, evaluation)
                    if beta <= alpha:
                        break
                return max_eval, best_move

            else:
                min_eval = float("inf")
                for start, end in all_moves:
                    saved = self._save_state()
                    self.move_piece(start, end)
                    evaluation, _ = self.minimax(depth - 1, alpha, beta, True)
                    self._restore_state(saved)

                    if evaluation < min_eval:
                        min_eval  = evaluation
                        best_move = (start, end)
                    beta = min(beta, evaluation)
                    if beta <= alpha:
                        break
                return min_eval, best_move

        finally:
            # Always restore sound, even if an exception occurs
            self._suppress_sound = False

    def _save_state(self):
        return (
            [row[:] for row in self.board],
            self.game_over,
            self.winner,
            self.turn,
        )

    def _restore_state(self, saved):
        self.board, self.game_over, self.winner, self.turn = saved

    def get_ai_move(self, difficulty="easy"):
        ai_team   = self.turn
        all_moves = []

        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                piece = self.board[r][c]
                if (ai_team == 1 and piece == 1) or (ai_team == 2 and piece in (2, 3)):
                    for move in self.get_valid_moves(r, c):
                        all_moves.append(((r, c), move))

        if not all_moves:
            return None

        if difficulty == "easy":
            return random.choice(all_moves)

        depth = 1 if difficulty == "medium" else 3
        _, move = self.minimax(
            depth,
            float("-inf"),
            float("inf"),
            maximizing_player=(ai_team == 2),
        )
        return move if move else random.choice(all_moves)

    # ----------------------------- Rendering -----------------------------

    def draw_board(self):
        self.screen.blit(self.board_img, (0, 0))

        # Highlight valid move targets
        for r, c in self.valid_moves:
            rect = pygame.Rect(
                PADDING_X + c * CELL_SIZE,
                PADDING_Y + r * CELL_SIZE,
                CELL_SIZE, CELL_SIZE,
            )
            self.screen.fill(COLOR_HIGHLIGHT, rect, pygame.BLEND_RGBA_MAX)

        # Draw pieces
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                piece = self.board[r][c]
                if piece == 0:
                    continue

                cell_x = PADDING_X + c * CELL_SIZE
                cell_y = PADDING_Y + r * CELL_SIZE

                # Highlight the selected piece
                if self.selected_piece == (r, c):
                    rect = pygame.Rect(cell_x, cell_y, CELL_SIZE, CELL_SIZE)
                    self.screen.fill(COLOR_HIGHLIGHT, rect, pygame.BLEND_RGBA_MAX)

                if self.images:
                    img   = self.images[piece]
                    img_x = cell_x + (CELL_SIZE - img.get_width())  // 2
                    img_y = cell_y + (CELL_SIZE - img.get_height()) // 2
                    self.screen.blit(img, (img_x, img_y))

    def draw_game_over(self):
        font     = pygame.font.SysFont("Arial", 24, bold=True)
        btn_font = pygame.font.SysFont("Arial", 18, bold=True)

        text     = font.render(self.winner, True, (200, 0, 0))
        btn_text = btn_font.render("Return to Main Menu", True, (245, 230, 200))

        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150))
        btn_rect  = btn_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 115))

        self.game_over_btn_rect = btn_rect.inflate(24, 14)
        bg_rect = text_rect.union(self.game_over_btn_rect).inflate(40, 30)

        if self.popup_bg_original:
            scaled_bg = pygame.transform.smoothscale(
                self.popup_bg_original, (bg_rect.width, bg_rect.height)
            )
            self.screen.blit(scaled_bg, bg_rect)
        else:
            pygame.draw.rect(self.screen, (255, 255, 255), bg_rect)

        pygame.draw.rect(self.screen, (0, 0, 0), bg_rect, 2)
        self.screen.blit(text, text_rect)

        pygame.draw.rect(self.screen, (30, 20, 15),   self.game_over_btn_rect)
        pygame.draw.rect(self.screen, (226, 188, 5),  self.game_over_btn_rect, 2)
        self.screen.blit(btn_text, btn_rect)

    # ----------------------------- Main Loop -----------------------------

    def run(self):
        while True:
            events = pygame.event.get()

            # Check for stalemate before processing input
            if not self.game_over and not self.menu_enabled:
                if not self.has_valid_moves(self.turn):
                    self.game_over = True
                    self.winner = (
                        "Defenders Win!" if self.turn == 1 else "Attackers Win!"
                    )
                    self.play_sound("ending")

            # --- Input Events ---
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.toggle_menu()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = pygame.mouse.get_pos()

                    if self.game_over:
                        if self.game_over_btn_rect.collidepoint(mx, my):
                            self.reset_game()
                            self.menu_enabled = True

                    elif not self.menu_enabled and self.turn != self.ai_player:
                        c = (mx - PADDING_X) // CELL_SIZE
                        r = (my - PADDING_Y) // CELL_SIZE

                        if (r, c) in self.valid_moves:
                            self.move_piece(self.selected_piece, (r, c))
                            self.selected_piece = None
                            self.valid_moves    = []
                        elif 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE:
                            self.selected_piece = (r, c)
                            self.valid_moves    = self.get_valid_moves(r, c)

            # --- AI Turn ---
            if not self.game_over and not self.menu_enabled and self.turn == self.ai_player:
                pygame.time.wait(400)
                ai_move = self.get_ai_move(difficulty=self.ai_difficulty)
                if ai_move:
                    start, end = ai_move
                    self.move_piece(start, end)
                self.selected_piece = None
                self.valid_moves    = []

            # --- Rendering ---
            self.draw_board()

            if self.game_over:
                self.draw_game_over()

            if self.menu_enabled:
                self.menu.update(events)
                self.menu.draw(self.screen)

            pygame.display.flip()
            self.clock.tick(FPS)


if __name__ == "__main__":
    game = BrandubhGame()
    game.run()

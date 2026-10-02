"""CrossOver game discovery. The user launches the game before starting tasks."""
from module.macos.window import find_game, require_permissions
from module.my_error.my_error import userStopError

class Game:
    def __init__(self, logger):
        self.log = logger

    def check_game_alive(self):
        try:
            find_game()
            return True
        except userStopError:
            return False

    def start_game(self):
        require_permissions()
        find_game()
        return True

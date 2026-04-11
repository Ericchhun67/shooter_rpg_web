from __future__ import annotations

import asyncio 
import sys
from pathlib import Path

try:
# Ensure the root directory itself is in the Python path for imports
    ROOT_DIR = Path(__file__).resolve().parent
    # This allows to import modules from the root directory without needing to specify the full path
    if str(ROOT_DIR) not in sys.path:
        # Insert the root directory at the beginning of sys.path to prioritize it for imports
        sys.path.insert(0, str(ROOT_DIR))
except Exception as e:
    print(f"An error occurred while setting up the Python path: {e}")

import pygame

from game.game import RiftbreakerGame


class GameError(Exception):
    """Custom exception for game-related errors."""
    pass


def display_fps(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font) -> None:
    """ 
    Display the FPS counter on the top-left corner of the screen. 
    """
    fps = int(clock.get_fps())
    fps_text = font.render(f"FPS: {fps}", True, (255, 255, 255))
    panel = pygame.Surface((fps_text.get_width() + 16, fps_text.get_height() + 10), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 140))
    screen.blit(panel, (8, 8))
    screen.blit(fps_text, (16, 13))
 

# Main game loop
async def main() -> None:
    game = RiftbreakerGame() # Initialize the game
    # Load the display_fps function into the game
    game.display_fps = lambda: display_fps(game.screen, game.clock, game.font_small)
    # handle any exceptions that occur during the game loop
    try:
        while game.running:
            # Calculate delta time
            dt = game.clock.tick(game.fps) / 1000.0
            game.handle_events() # Handle user input and events
            game.update(dt) # Update game state based on delta time
            game.draw() # Render the game state to the screen
            game.display_fps()
            pygame.display.flip()
            await asyncio.sleep(0)
        pygame.quit() # Clean up and exit the game
    except Exception as e:
        print(f"An error occurred: {e}")
        pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())

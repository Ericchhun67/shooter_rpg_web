from __future__ import annotations

import asyncio 
import sys
import traceback
from pathlib import Path

# Set up the pthon path to include the root directory of the project for imports
# try-except block to handle any potential issues with modifying the python path, 
# such as permission errors to access the file system or issues with the __file__ attribute
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



# Function to display the FPS counter on the screen
def display_fps(screen: pygame.Surface, clock: pygame.time.Clock, font: pygame.font.Font) -> None:
    """ 
    Display the FPS counter on the top-left corner of the screen. 
    """
    fps = int(clock.get_fps()) # Get the current frames per second from the clock
    fps_text = font.render(f"FPS: {fps}", True, (255, 255, 255)) # Render the FPS text using the provided font
    panel = pygame.Surface((fps_text.get_width() + 16, fps_text.get_height() + 10), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 140)) # Create a semi-transparent black panel to improve readability
    # blit the panel and the FPS text onto the screen at the top-left corner with some padding
    screen.blit(panel, (8, 8))
    screen.blit(fps_text, (16, 13))


def show_startup_error(message: str) -> None:
    if not pygame.get_init():
        pygame.init()
    screen = pygame.display.get_surface()
    if screen is None:
        screen = pygame.display.set_mode((960, 640))
    pygame.display.set_caption("Riftbreaker Protocol Error")
    font_title = pygame.font.SysFont("consolas", 28, bold=True)
    font_body = pygame.font.SysFont("consolas", 20)
    screen.fill((18, 20, 28))
    panel = pygame.Rect(60, 60, screen.get_width() - 120, screen.get_height() - 120)
    pygame.draw.rect(screen, (34, 39, 52), panel, border_radius=16)
    pygame.draw.rect(screen, (215, 92, 92), panel, 3, border_radius=16)
    screen.blit(font_title.render("Startup Error", True, (255, 230, 230)), (panel.x + 24, panel.y + 22))

    lines: list[str] = []
    for raw_line in message.splitlines() or [message]:
        line = raw_line.rstrip() or " "
        while len(line) > 88:
            lines.append(line[:88])
            line = line[88:]
        lines.append(line)

    y = panel.y + 72
    for line in lines[:20]:
        label = font_body.render(line, True, (232, 236, 243))
        screen.blit(label, (panel.x + 24, y))
        y += 26
    pygame.display.flip()
 

# Main game loop
async def main() -> None:
    game = None
    try:
        game = RiftbreakerGame() # Initialize the game
        # Load the display_fps function into the game
        game.display_fps = lambda: display_fps(game.screen, game.clock, game.font_small)
        # handle any exceptions that occur during the game loop
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
        # Catch any exceptions that occur during the game loop and print an error
        # message to the console, then quit the game gracefully
        error_text = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        print(error_text)
        try:
            show_startup_error(error_text)
            for _ in range(600):
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        raise SystemExit
                await asyncio.sleep(1 / 60)
        finally:
            pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())

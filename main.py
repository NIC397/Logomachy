import pygame
import sys
import random
import threading
import time
import google.generativeai as genai
import json
import os
import math
from dotenv import load_dotenv

# Initialize Pygame
pygame.init()

# Set up the display
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Logomachy")

# Set up the clock for 60 FPS
clock = pygame.time.Clock()
FPS = 60

# Colors
DARK_COLOR = (20, 20, 30)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (100, 150, 255)
RED = (255, 100, 100)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)
PURPLE = (150, 100, 255)
GREEN = (100, 255, 100)
ORANGE = (255, 165, 0)


# Game variables
active_player = 1  # 1 or 2, alternates each round
current_input_text = ""

# Attacker/defender role tracking
round_state = {
    'attacker': 1,  # 1 or 2
    'defender': 2,  # 1 or 2
}

# Dual input boxes
player1_box = pygame.Rect(50, WINDOW_HEIGHT - 50, (WINDOW_WIDTH - 120) // 2, 30)
player2_box = pygame.Rect(WINDOW_WIDTH - 50 - (WINDOW_WIDTH - 120) // 2, WINDOW_HEIGHT - 50, (WINDOW_WIDTH - 120) // 2, 30)

# Input system state
input_state = {
    'player1_text': "",
    'player2_text': "",
    'player1_locked': False,
    'player2_locked': False,
    'active_box': 1,  # 1 or 2
    'battle_phase': 'preparation',  # 'preparation', 'battle', 'result'
    'waiting_for_judgment': False,
    'attacker_locked': False,  # True after attacker locks
    'defender_locked': False,  # True after defender locks
}

# Particle system for explosion effects
particles = []

# Wizard state tracking
wizard_states = {
    'player1': {
        'exploding': False,
        'explosion_timer': 0,
        'broken': False,  # New state to track if wizard is broken
        'reconstruction_particles': []  # Store particles for reconstruction
    },
    'player2': {
        'exploding': False,
        'explosion_timer': 0,
        'broken': False,
        'reconstruction_particles': []
    }
}

# Fonts for text rendering
font = pygame.font.Font(None, 36)
title_font = pygame.font.Font(None, 48)
subtitle_font = pygame.font.Font(None, 42)
small_font = pygame.font.Font(None, 28)

# Active spells list
active_spells = []

# Configure Google Generative AI
load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_KEY'))


# System prompt for the Mad God of Magic
SYSTEM_PROMPT = """You are the Mad God of Magic, an ancient and capricious deity who presides over magical duels. You have witnessed countless spell battles throughout the eons, and your judgment is both feared and respected by all who practice the arcane arts.

Your role is to judge magical duels between two spells cast by competing wizards. You must determine which spell is more powerful, more clever, or more effective based on:

1. **Magical Power**: The raw magical energy and potency of the spell
2. **Cunning**: The cleverness and strategic thinking behind the spell
3. **Creativity**: The originality and imaginative use of magic
4. **Effectiveness**: How well the spell would work in a real magical duel
5. **Style**: The elegance and artistry of the spell's execution

You are known for your unpredictable nature. Sometimes you favor raw power, sometimes subtlety, sometimes pure creativity. Your decisions are often surprising and sometimes seem arbitrary, but they always carry the weight of divine authority.

When judging a duel, you must respond with a JSON object containing:
- "reasoning": A brief, dramatic explanation of your decision (2-3 sentences, written in the voice of an ancient, powerful deity)
- "winner": Either "PLAYER_1", "PLAYER_2", or "OFFSET" (if the spells are equally matched and cancel each other out)

Remember: You are the Mad God of Magic. Your word is law, and your judgments are final. Be dramatic, be mysterious, be the capricious deity you are.

Your response MUST be a JSON object with 'reasoning' and 'winner' (PLAYER_1, PLAYER_2, or OFFSET)."""

# Game state for passing results between threads
game_state = {
    'judgments_queue': [],
    'display_reasoning': None,
    'reasoning_timestamp': None,
    'judgment_history': [],  # Store all previous judgments
    'paused': False,         # Pause state
    'game_over': False,      # Game over state
    'current_screen': 'title',  # 'title', 'tutorial', 'game', or 'thankyou'
}

thankyou_letters = []
thankyou_letters_initialized = False
thankyou_timer = 0

def draw_thankyou_screen():
    """Draw a thank you screen with black background, 26 slow bouncing alphabet letters, and dancing wizards"""
    global thankyou_letters, thankyou_letters_initialized, thankyou_timer
    # Black background
    screen.fill((0, 0, 0))

    # Initialize 26 alphabet letters, 13 blue, 13 red, slow speed
    if not thankyou_letters_initialized or len(thankyou_letters) != 26:
        thankyou_letters = []
        alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        random.shuffle(alphabet)
        blue_letters = alphabet[:13]
        red_letters = alphabet[13:]
        for i, char in enumerate(blue_letters):
            x = random.randint(40, WINDOW_WIDTH - 80)
            y = random.randint(80, WINDOW_HEIGHT - 180)
            vx = random.choice([-1, 1]) * random.uniform(1.0, 2.0)
            vy = random.choice([-1, 1]) * random.uniform(1.0, 2.0)
            thankyou_letters.append({'char': char, 'x': x, 'y': y, 'vx': vx, 'vy': vy, 'color': BLUE})
        for i, char in enumerate(red_letters):
            x = random.randint(40, WINDOW_WIDTH - 80)
            y = random.randint(80, WINDOW_HEIGHT - 180)
            vx = random.choice([-1, 1]) * random.uniform(1.0, 2.0)
            vy = random.choice([-1, 1]) * random.uniform(1.0, 2.0)
            thankyou_letters.append({'char': char, 'x': x, 'y': y, 'vx': vx, 'vy': vy, 'color': RED})
        thankyou_letters_initialized = True

    # Move and draw flying letters
    letter_font = pygame.font.Font(None, 80)
    letter_width = 48
    letter_height = 80
    for letter in thankyou_letters:
        letter['x'] += letter['vx']
        letter['y'] += letter['vy']
        # Bounce at edges, keep fully on screen
        if letter['x'] < 0:
            letter['x'] = 0
            letter['vx'] *= -1
        if letter['x'] > WINDOW_WIDTH - letter_width:
            letter['x'] = WINDOW_WIDTH - letter_width
            letter['vx'] *= -1
        if letter['y'] < 0:
            letter['y'] = 0
            letter['vy'] *= -1
        if letter['y'] > WINDOW_HEIGHT - letter_height//2:
            letter['y'] = WINDOW_HEIGHT - letter_height//2
            letter['vy'] *= -1
        surf = letter_font.render(letter['char'], True, letter['color'])
        screen.blit(surf, (int(letter['x']), int(letter['y'])))

    # Draw two dancing wizards
    thankyou_timer += 1
    def draw_dancing_wizard(x, y, color, flip=False, t=0):
        # Bobbing
        bob = int(10 * math.sin(t / 10.0 + (0 if not flip else math.pi)))
        y += bob
        # Arms up/down
        arm_angle = 30 * math.sin(t / 7.0 + (0 if not flip else math.pi))
        # Hat
        hat_points = [
            (x, y - 50),
            (x - 20, y - 35),
            (x + 20, y - 35),
        ]
        pygame.draw.polygon(screen, color, hat_points)
        pygame.draw.ellipse(screen, color, (x - 25, y - 40, 50, 15))
        # Head
        pygame.draw.circle(screen, (255, 220, 177), (x, y - 30), 15)
        # Eyes (open)
        pygame.draw.circle(screen, BLACK, (x - 5, y - 32), 2)
        pygame.draw.circle(screen, BLACK, (x + 5, y - 32), 2)
        # Beard
        pygame.draw.ellipse(screen, (200, 200, 200), (x - 8, y - 20, 16, 12))
        # Body (robe)
        pygame.draw.line(screen, color, (x, y - 15), (x, y + 30), 8)
        # Arms (dancing)
        arm_len = 35
        angle_rad = math.radians(arm_angle)
        ax1 = x - int(arm_len * math.cos(angle_rad))
        ay1 = y + int(arm_len * math.sin(angle_rad))
        ax2 = x + int(arm_len * math.cos(angle_rad))
        ay2 = y + int(arm_len * math.sin(angle_rad))
        pygame.draw.line(screen, color, (x, y), (ax1, ay1), 6)
        pygame.draw.line(screen, color, (x, y), (ax2, ay2), 6)
        # Legs
        pygame.draw.line(screen, color, (x, y + 30), (x - 15, y + 50), 6)
        pygame.draw.line(screen, color, (x, y + 30), (x + 15, y + 50), 6)
        # Staff (wiggle)
        staff_angle = 10 * math.sin(t / 13.0 + (0 if not flip else math.pi))
        staff_rad = math.radians(staff_angle)
        sx = x + 25
        sy = y - 10
        ex = sx + int(30 * math.cos(staff_rad))
        ey = sy + int(30 * math.sin(staff_rad))
        pygame.draw.line(screen, (139, 69, 19), (sx, sy), (ex, ey), 4)
        pygame.draw.circle(screen, (255, 255, 0), (ex, ey), 6)

    draw_dancing_wizard(300, 420, BLUE, flip=False, t=thankyou_timer)
    draw_dancing_wizard(700, 420, RED, flip=True, t=thankyou_timer)

    # Draw big thank you text (static, on top)
    thank_font = pygame.font.Font(None, 90)
    thank_surface = thank_font.render("Thank You For Playing!", True, GOLD)
    thank_rect = thank_surface.get_rect(center=(WINDOW_WIDTH // 2, 120))
    screen.blit(thank_surface, thank_rect)

# Tutorial state for handling the intro screen
tutorial_state = {
    'scroll_offset': 0,  # For scrolling effect if needed
    'highlight_timer': 0,  # For highlighting important text
}

# Title screen state
title_state = {
    'letter_particles': [],  # Particles for title animation
    'press_space_scale': 1.0,  # For breathing effect
    'scale_increasing': True,  # Direction of breathing effect
    'title_timer': 0,  # For timing various effects
    'floating_wizards': [
        {'x': 200, 'y': 300, 'dy': 0, 'color': BLUE},  # Left wizard
        {'x': 800, 'y': 300, 'dy': 0, 'color': RED}   # Right wizard
    ]
}

# Large title font
title_large_font = pygame.font.Font(None, 120)
breathing_font = pygame.font.Font(None, 48)

class Spell:
    def __init__(self, text, pos, direction, player_id):
        self.text = text
        self.pos = list(pos)  # Convert to list for easy modification
        self.direction = direction
        self.player_id = player_id
        self.speed = 3  # Pixels per frame
        self.state = 'flying'  # 'flying' or 'tangling'
        self.id = random.randint(1, 1000000)  # Unique ID for each spell
        self.font = pygame.font.Font(None, 36)
        # Create rect by rendering text and getting its size
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        self.rect = text_surface.get_rect(topleft=self.pos)
    
    def move(self):
        """Move the spell based on its direction"""
        if self.state == 'flying':
            if self.direction == 'right':
                self.pos[0] += self.speed
            elif self.direction == 'left':
                self.pos[0] -= self.speed
            
            # Update the rect position
            self.rect.topleft = (int(self.pos[0]), int(self.pos[1]))
    
    def draw(self, screen):
        """Draw the spell text on screen"""
        # Choose color based on player
        color = BLUE if self.player_id == 1 else RED
        
        # Render the text
        text_surface = self.font.render(self.text, True, color)
        
        # Calculate draw position
        draw_x = int(self.pos[0])
        draw_y = int(self.pos[1])
        
        # Add jiggle effect if tangling
        if self.state == 'tangling':
            draw_x += random.randint(-2, 2)
            draw_y += random.randint(-2, 2)
        
        screen.blit(text_surface, (draw_x, draw_y))

def get_real_judgment(spell1_id, spell1_text, spell2_id, spell2_text):
    """Use the real LLM judge to make a decision about two tangling spells"""
    print(f"MAD GOD: Contemplating {spell1_text} vs {spell2_text}...")
    
    try:
        # Set up the model
        model = genai.GenerativeModel('gemini-flash-lite-latest')
        
        # Create the user message
        user_message = f"Spell 1: '{spell1_text}'\nSpell 2: '{spell2_text}'"
        
        # Generate content
        response = model.generate_content([SYSTEM_PROMPT, user_message])
        
        # Clean the response text by removing markdown formatting
        response_text = response.text.strip()
        if response_text.startswith('```json'):
            response_text = response_text[7:]  # Remove ```json
        if response_text.startswith('```'):
            response_text = response_text[3:]   # Remove ```
        if response_text.endswith('```'):
            response_text = response_text[:-3]  # Remove trailing ```
        response_text = response_text.strip()
        
        # Try to parse the JSON
        result_json = json.loads(response_text)
        
        # Create the final result dictionary
        result = {
            'spell1_id': spell1_id,
            'spell2_id': spell2_id,
            'winner': result_json['winner'],
            'reasoning': result_json['reasoning']
        }
        
        # Add result to the queue
        game_state['judgments_queue'].append(result)
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Raw response: {response.text}")
        # Fallback to random decision
        result = {
            'spell1_id': spell1_id,
            'spell2_id': spell2_id,
            'winner': random.choice(['PLAYER_1', 'PLAYER_2', 'OFFSET']),
            'reasoning': 'The Mad God\'s response was too chaotic to understand. A random decision was made.'
        }
        game_state['judgments_queue'].append(result)
        
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        # Fallback to random decision
        result = {
            'spell1_id': spell1_id,
            'spell2_id': spell2_id,
            'winner': random.choice(['PLAYER_1', 'PLAYER_2', 'OFFSET']),
            'reasoning': 'The Mad God is temporarily unavailable. A random decision was made.'
        }
        game_state['judgments_queue'].append(result)

def wrap_text(text, font, max_width):
    """Wrap text to fit within the specified width"""
    words = text.split(' ')
    lines = []
    current_line = []
    
    for word in words:
        # Test if adding this word would exceed the width
        test_line = ' '.join(current_line + [word])
        test_surface = font.render(test_line, True, (255, 255, 255))
        
        if test_surface.get_width() <= max_width:
            current_line.append(word)
        else:
            # If current line has content, add it to lines and start new line
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Single word is too long, add it anyway
                lines.append(word)
    
    # Add the last line if it has content
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def draw_judgment_display(screen, reasoning_text, winner=None):
    """Draw a beautiful judgment display in the center of the screen"""
    # Create a semi-transparent background panel
    panel_width = WINDOW_WIDTH - 80
    panel_height = 250
    panel_x = (WINDOW_WIDTH - panel_width) // 2
    panel_y = (WINDOW_HEIGHT - panel_height) // 3
    
    # Draw title
    title_surface = title_font.render("MAD GOD'S JUDGMENT", True, GOLD)
    title_rect = title_surface.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 30))
    screen.blit(title_surface, title_rect)
    
    # Draw winner if provided
    if winner:
        if winner == 'PLAYER_1':
            winner_text = "WINNER: PLAYER 1"
            winner_color = BLUE
        elif winner == 'PLAYER_2':
            winner_text = "WINNER: PLAYER 2"
            winner_color = RED
        else:  # OFFSET
            winner_text = "MUTUAL DESTRUCTION"
            winner_color = ORANGE
        
        winner_surface = subtitle_font.render(winner_text, True, winner_color)
        winner_rect = winner_surface.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 70))
        screen.blit(winner_surface, winner_rect)
    
    # Wrap and draw reasoning text
    max_width = panel_width - 40
    wrapped_lines = wrap_text(reasoning_text, font, max_width)
    
    # Calculate starting position for text
    text_start_y = panel_y + (120 if winner else 80)
    line_height = 28
    
    for i, line in enumerate(wrapped_lines):
        if line.strip():
            # Alternate colors for visual appeal
            color = WHITE if i % 2 == 0 else SILVER
            reasoning_surface = font.render(line.strip(), True, color)
            text_rect = reasoning_surface.get_rect(center=(WINDOW_WIDTH // 2, text_start_y + i * line_height))
            screen.blit(reasoning_surface, text_rect)

def draw_judgment_history(screen, font, history):
    """Draw the most recent 3 judgments with beautiful styling"""
    if not history:
        # Show message if no history
        no_history_surface = title_font.render("No judgment history yet", True, GOLD)
        text_rect = no_history_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
        screen.blit(no_history_surface, text_rect)
        
        close_surface = small_font.render("Press ` to close", True, SILVER)
        close_rect = close_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 40))
        screen.blit(close_surface, close_rect)
        return
    
    # Draw semi-transparent background
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(220)
    overlay.fill((10, 10, 20))
    screen.blit(overlay, (0, 0))
    
    title_surface = title_font.render("JUDGMENT ARCHIVES", True, PURPLE)
    title_text_rect = title_surface.get_rect(center=(WINDOW_WIDTH // 2, 60))
    screen.blit(title_surface, title_text_rect)
    
    # Draw instructions
    inst_surface = small_font.render("Press ` to close | ESC to exit", True, SILVER)
    screen.blit(inst_surface, (50, 100))
    
    # Draw the most recent 2 judgments
    y_start = 140
    for i, judgment in enumerate(history):
        y_pos = y_start + i * 140
        
        # Draw judgment number
        num_surface = small_font.render(f"#{i}", True, GOLD)
        screen.blit(num_surface, (50, y_pos + 10))
        
        # Draw spells with color-coded styling
        spell1_text = f"'{judgment['spell1_text']}'"
        spell2_text = f"'{judgment['spell2_text']}'"
        vs_text = " vs "
        
        # Render each part with appropriate colors
        spell1_surface = font.render(spell1_text, True, BLUE)
        vs_surface = font.render(vs_text, True, WHITE)
        spell2_surface = font.render(spell2_text, True, RED)
        
        # Calculate positions
        spell1_width = spell1_surface.get_width()
        vs_width = vs_surface.get_width()
        
        screen.blit(spell1_surface, (50, y_pos + 35))
        screen.blit(vs_surface, (50 + spell1_width, y_pos + 35))
        screen.blit(spell2_surface, (50 + spell1_width + vs_width, y_pos + 35))
        
        # Draw winner with better colors
        if judgment['winner'] == 'PLAYER_1':
            winner_color = BLUE
            winner_text = "Player 1 Victory"
        elif judgment['winner'] == 'PLAYER_2':
            winner_color = RED
            winner_text = "Player 2 Victory"
        else:
            winner_color = ORANGE
            winner_text = "Mutual Destruction"
            
        winner_surface = font.render(winner_text, True, winner_color)
        screen.blit(winner_surface, (50, y_pos + 65))
        
        # Draw reasoning (wrapped) with better styling
        max_width = WINDOW_WIDTH - 120
        wrapped_reasoning = wrap_text(judgment['reasoning'], small_font, max_width)
        for j, line in enumerate(wrapped_reasoning[:2]):  # Limit to 2 lines
            if line.strip():
                reasoning_surface = small_font.render(line.strip(), True, (220, 220, 220))
                screen.blit(reasoning_surface, (60, y_pos + 90 + j * 18))

def draw_pause_screen(screen, history):
    """Draw the pause screen with history and controls"""
    # Draw semi-transparent background
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.set_alpha(240)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))
    
    # Draw main title
    title_surface = title_font.render("GAME PAUSED", True, GOLD)
    title_rect = title_surface.get_rect(center=(WINDOW_WIDTH // 2, 80))
    screen.blit(title_surface, title_rect)
    
    # Draw controls
    controls = [
        "ESC - Resume Game",
        "Q - Quit Game", 
        "R - Restart Game"
    ]
    
    y_pos = 120
    for control in controls:
        control_surface = font.render(control, True, WHITE)
        control_rect = control_surface.get_rect(center=(WINDOW_WIDTH // 2, y_pos))
        screen.blit(control_surface, control_rect)
        y_pos += 35
    
    # Draw history section
    if history:
        # Draw history title
        history_title = title_font.render("RECENT JUDGMENTS", True, PURPLE)
        history_title_rect = history_title.get_rect(center=(WINDOW_WIDTH // 2, 250))
        screen.blit(history_title, history_title_rect)
        
        # Draw history cards
        y_start = 300
        for i, judgment in enumerate(history):
            y_pos = y_start + i * 140
            
            # Draw judgment number
            num_surface = small_font.render(f"#{len(history) - i}", True, GOLD)
            screen.blit(num_surface, (50, y_pos + 10))
            
            # Draw spells with color-coded styling
            spell1_text = f"'{judgment['spell1_text']}'"
            spell2_text = f"'{judgment['spell2_text']}'"
            vs_text = " vs "
            
            # Render each part with appropriate colors
            spell1_surface = font.render(spell1_text, True, BLUE)
            vs_surface = font.render(vs_text, True, WHITE)
            spell2_surface = font.render(spell2_text, True, RED)
            
            # Calculate positions
            spell1_width = spell1_surface.get_width()
            vs_width = vs_surface.get_width()
            
            screen.blit(spell1_surface, (50, y_pos + 35))
            screen.blit(vs_surface, (50 + spell1_width, y_pos + 35))
            screen.blit(spell2_surface, (50 + spell1_width + vs_width, y_pos + 35))
            
            # Draw winner
            if judgment['winner'] == 'PLAYER_1':
                winner_color = BLUE
                winner_text = "Player 1 Victory"
            elif judgment['winner'] == 'PLAYER_2':
                winner_color = RED
                winner_text = "Player 2 Victory"
            else:
                winner_color = ORANGE
                winner_text = "Mutual Destruction"
                
            winner_surface = font.render(winner_text, True, winner_color)
            screen.blit(winner_surface, (50, y_pos + 65))
            
            # Draw reasoning (wrapped)
            max_width = WINDOW_WIDTH - 120
            wrapped_reasoning = wrap_text(judgment['reasoning'], small_font, max_width)
            for j, line in enumerate(wrapped_reasoning[:3]):  # Limit to 2 lines
                if line.strip():
                    reasoning_surface = small_font.render(line.strip(), True, (220, 220, 220))
                    screen.blit(reasoning_surface, (60, y_pos + 90 + j * 18))
    else:
        # No history message
        no_history_surface = title_font.render("No judgments yet", True, SILVER)
        no_history_rect = no_history_surface.get_rect(center=(WINDOW_WIDTH // 2, 350))
        screen.blit(no_history_surface, no_history_rect)

def draw_input_boxes(screen):
    """Draw the dual input boxes with proper styling"""
    # Draw Player 1 box
    box1_color = GOLD if input_state['active_box'] == 1 else WHITE
    box1_bg = (40, 40, 60) if input_state['player1_locked'] else (20, 20, 30)
    pygame.draw.rect(screen, box1_bg, player1_box)
    pygame.draw.rect(screen, box1_color, player1_box, 3)
    
    # Draw Player 2 box
    box2_color = GOLD if input_state['active_box'] == 2 else WHITE
    box2_bg = (40, 40, 60) if input_state['player2_locked'] else (20, 20, 30)
    pygame.draw.rect(screen, box2_bg, player2_box)
    pygame.draw.rect(screen, box2_color, player2_box, 3)
    
    # Draw player labels
    player1_label = "Player 1" + (" (LOCKED)" if input_state['player1_locked'] else "")
    player2_label = "Player 2" + (" (LOCKED)" if input_state['player2_locked'] else "")
    
    label1_surface = small_font.render(player1_label, True, box1_color)
    label2_surface = small_font.render(player2_label, True, box2_color)
    
    screen.blit(label1_surface, (player1_box.x, player1_box.y - 25))
    screen.blit(label2_surface, (player2_box.x, player2_box.y - 25))
    
    # Draw text content
    text1_surface = font.render(input_state['player1_text'], True, WHITE)
    text2_surface = font.render(input_state['player2_text'], True, WHITE)
    
    screen.blit(text1_surface, (player1_box.x + 5, player1_box.y + 5))
    screen.blit(text2_surface, (player2_box.x + 5, player2_box.y + 5))
    
    # Draw cursor for active box
    if not (input_state['active_box'] == 1 and input_state['player1_locked']) and not (input_state['active_box'] == 2 and input_state['player2_locked']):
        cursor_x = (player1_box.x + 5 + font.size(input_state['player1_text'])[0] if input_state['active_box'] == 1 
                   else player2_box.x + 5 + font.size(input_state['player2_text'])[0])
        cursor_y = player1_box.y + 5 if input_state['active_box'] == 1 else player2_box.y + 5
        pygame.draw.line(screen, WHITE, (cursor_x, cursor_y), (cursor_x, cursor_y + 25), 2)

def draw_phase_indicator(screen):
    """Draw the current battle phase indicator with attacker/defender roles"""
    if input_state['battle_phase'] == 'preparation':
        attacker = round_state['attacker']
        defender = round_state['defender']
        if not input_state['attacker_locked']:
            phase_text = f"Player {attacker} is the ATTACKER. Enter your spell and press Enter to lock."
        elif not input_state['defender_locked']:
            phase_text = f"Player {defender} is the DEFENDER. Enter your spell and press Enter to lock."
        else:
            phase_text = "Both spells ready! Battle will begin."
    elif input_state['battle_phase'] == 'battle':
        phase_text = "BATTLE IN PROGRESS - Spells are colliding!"
    elif input_state['battle_phase'] == 'result':
        phase_text = "Press SPACE to continue to next round"
    
    phase_surface = font.render(phase_text, True, GOLD)
    phase_rect = phase_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 120))
    screen.blit(phase_surface, phase_rect)

def draw_wizard(screen, x, y, color):
    """Draw a wizard figure at the given position"""
    # Wizard hat (pointed hat)
    hat_points = [
        (x, y - 50),  # Top point
        (x - 20, y - 35),  # Left side
        (x + 20, y - 35),  # Right side
    ]
    pygame.draw.polygon(screen, color, hat_points)
    
    # Hat brim
    pygame.draw.ellipse(screen, color, (x - 25, y - 40, 50, 15))
    
    # Head (circle)
    pygame.draw.circle(screen, (255, 220, 177), (x, y - 30), 15)
    
    # Eyes
    pygame.draw.circle(screen, (0, 0, 0), (x - 5, y - 32), 2)
    pygame.draw.circle(screen, (0, 0, 0), (x + 5, y - 32), 2)
    
    # Beard
    pygame.draw.ellipse(screen, (200, 200, 200), (x - 8, y - 20, 16, 12))
    
    # Body (robe)
    pygame.draw.line(screen, color, (x, y - 15), (x, y + 30), 4)
    
    # Arms (in robe)
    pygame.draw.line(screen, color, (x, y), (x - 20, y + 10), 4)
    pygame.draw.line(screen, color, (x, y), (x + 20, y + 10), 4)
    
    # Legs
    pygame.draw.line(screen, color, (x, y + 30), (x - 15, y + 50), 4)
    pygame.draw.line(screen, color, (x, y + 30), (x + 15, y + 50), 4)
    
    # Staff (magic wand)
    pygame.draw.line(screen, (139, 69, 19), (x + 25, y - 10), (x + 25, y + 20), 3)
    # Staff tip (crystal)
    pygame.draw.circle(screen, (255, 255, 0), (x + 25, y - 15), 4)

class Particle:
    def __init__(self, x, y, color, text_char):
        self.x = x
        self.y = y
        self.color = color
        self.text_char = text_char
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-8, -2)
        self.gravity = 0.3
        self.life = 60  # frames
        self.max_life = 60
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-10, 10)
        self.scale = 1.0
        self.scale_speed = -0.02
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1
        self.rotation += self.rotation_speed
        self.scale += self.scale_speed
        self.scale = max(0.1, self.scale)
    
    def draw(self, screen):
        if self.life > 0:
            # Create rotated and scaled text
            # Use even smaller font for particles
            particle_font = pygame.font.Font(None, 24)
            char_surface = particle_font.render(self.text_char, True, self.color)
            # Apply rotation and scaling (simplified)
            alpha = int(255 * (self.life / self.max_life))
            char_surface.set_alpha(alpha)
            screen.blit(char_surface, (int(self.x), int(self.y)))
    
    def is_alive(self):
        return self.life > 0

def create_explosion_effect(x, y, text, color):
    """Create explosion particles from text"""
    global particles
    for i, char in enumerate(text):
        if char != ' ':  # Don't create particles for spaces
            # Spread particles around the text position
            offset_x = (i - len(text) / 2) * 8
            particle = Particle(x + offset_x, y, color, char)
            particles.append(particle)

def create_wizard_explosion(x, y, color):
    """Create explosion particles for wizard destruction"""
    global particles
    # Create multiple particles for different wizard parts
    wizard_parts = ['*', '^', 'o', '+', 'x', '#', '@', '%', '&']
    explosion_particles = []
    
    for i in range(20):  # More particles for wizard explosion
        part_char = random.choice(wizard_parts)
        # Spread particles in all directions around wizard
        angle = random.uniform(0, 2 * 3.14159)
        distance = random.uniform(10, 40)
        offset_x = distance * random.uniform(-1, 1)
        offset_y = distance * random.uniform(-1, 1)
        
        particle = Particle(x + offset_x, y + offset_y, color, part_char)
        # Make wizard particles more dramatic
        particle.vx = random.uniform(-8, 8)
        particle.vy = random.uniform(-10, -3)
        particle.life = 90  # Longer lasting
        particle.max_life = 90
        particles.append(particle)
        explosion_particles.append({
            'char': part_char,
            'final_x': x + offset_x,
            'final_y': y + offset_y
        })
    return explosion_particles

def create_wizard_reconstruction(x, y, color, stored_particles):
    """Create reconstruction effect for wizard reform"""
    global particles
    
    for particle_info in stored_particles:
        # Create particles that will move towards their final positions
        start_x = particle_info['final_x'] + random.uniform(-100, 100)  # Start from random positions
        start_y = particle_info['final_y'] + random.uniform(-100, 100)
        
        # Calculate velocity to reach the final position
        dx = (particle_info['final_x'] - start_x) / 30  # Take 30 frames to reach target
        dy = (particle_info['final_y'] - start_y) / 30
        
        particle = Particle(start_x, start_y, color, particle_info['char'])
        particle.vx = dx
        particle.vy = dy
        particle.gravity = 0  # No gravity for reconstruction
        particle.life = 30  # Time to reach position
        particle.max_life = 30
        particles.append(particle)

def check_wizard_hits():
    """Check if any spells hit the wizards"""
    global wizard_states, active_spells
    
    # Wizard positions
    wizard1_x = 100  # Player 1 wizard x position
    wizard2_x = 900  # Player 2 wizard x position
    wizard_width = 40  # Width of wizard hitbox
    wizard_y = 500   # Y position of wizards
    wizard_height = 100  # Height of wizard hitbox
    
    # Create a list to store spells that need to be removed
    spells_to_remove = []
    
    for spell in active_spells[:]:  # Create a copy of the list to safely modify it
        # Get spell's leading edge position based on direction
        if spell.direction == 'right':
            spell_edge_x = spell.pos[0] + spell.rect.width  # Right edge of text
        else:  # direction == 'left'
            spell_edge_x = spell.pos[0]  # Left edge of text
            
        spell_y = spell.pos[1]  # Vertical position of spell
        
        # Check if spell hits Player 1 wizard
        if spell.player_id == 2:  # Enemy spell moving left
            # Check if spell's left edge reaches wizard 1's hitbox and is at the right height
            if (spell_edge_x <= wizard1_x + wizard_width and 
                spell.pos[0] + spell.rect.width >= wizard1_x and  # Hasn't passed through completely
                abs(spell_y - wizard_y) < wizard_height and  # Check vertical alignment
                not wizard_states['player1']['exploding']):
                wizard_states['player1']['exploding'] = True
                wizard_states['player1']['explosion_timer'] = 60
                # Store explosion particles for later reconstruction
                wizard_states['player1']['reconstruction_particles'] = create_wizard_explosion(wizard1_x, wizard_y, BLUE)
                # Create spell explosion at the point of impact
                create_explosion_effect(spell_edge_x, spell_y, spell.text, RED)
                spells_to_remove.append(spell)
                print("Player 1 wizard hit!")
        
        # Check if spell hits Player 2 wizard
        elif spell.player_id == 1:  # Enemy spell moving right
            # Check if spell's right edge reaches wizard 2's hitbox and is at the right height
            if (spell_edge_x >= wizard2_x and 
                spell.pos[0] <= wizard2_x + wizard_width and  # Hasn't passed through completely
                abs(spell_y - wizard_y) < wizard_height and  # Check vertical alignment
                not wizard_states['player2']['exploding']):
                wizard_states['player2']['exploding'] = True
                wizard_states['player2']['explosion_timer'] = 60
                # Store explosion particles for later reconstruction
                wizard_states['player2']['reconstruction_particles'] = create_wizard_explosion(wizard2_x, wizard_y, RED)
                # Create spell explosion at the point of impact
                create_explosion_effect(spell_edge_x, spell_y, spell.text, BLUE)
                spells_to_remove.append(spell)
                print("Player 2 wizard hit!")
    
    # Remove all spells that hit wizards
    for spell in spells_to_remove:
        if spell in active_spells:
            active_spells.remove(spell)
            # Reset battle phase if no spells remain
            if not active_spells:
                input_state['battle_phase'] = 'result'

def update_wizard_states():
    """Update wizard explosion states"""
    global wizard_states
    
    for player in ['player1', 'player2']:
        if wizard_states[player]['exploding']:
            wizard_states[player]['explosion_timer'] -= 1
            if wizard_states[player]['explosion_timer'] <= 0:
                wizard_states[player]['exploding'] = False
                wizard_states[player]['broken'] = True  # Mark wizard as broken after explosion

def update_particles():
    """Update all particles"""
    global particles
    particles = [p for p in particles if p.is_alive()]
    for particle in particles:
        particle.update()

def draw_particles(screen):
    """Draw all particles"""
    for particle in particles:
        particle.draw(screen)

def draw_tutorial_screen():
    """Draw the game's tutorial/intro screen"""
    global tutorial_state
    
    # Create a semi-transparent dark background
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    overlay.fill(DARK_COLOR)
    overlay.set_alpha(240)
    screen.blit(overlay, (0, 0))
    
    # Title
    title_text = "How to Play"
    title_surface = title_font.render(title_text, True, GOLD)
    title_rect = title_surface.get_rect(center=(WINDOW_WIDTH // 2, 80))
    screen.blit(title_surface, title_rect)
    
    # Concise tutorial message
    concise_lines = [
        ("Use powerful language to cast spells!", WHITE),
        ("Your incantation must counter your opponent's spell.", WHITE),
        ("The Mad God will judge whose magic prevails.", WHITE)
    ]
    y_pos = 200
    for text, color in concise_lines:
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(centerx=WINDOW_WIDTH // 2)
        text_rect.y = y_pos
        screen.blit(text_surface, text_rect)
        y_pos += 40
    
    # Draw pulsing "Press Space to Start" text at the bottom
    tutorial_state['highlight_timer'] = (tutorial_state['highlight_timer'] + 1) % 60
    alpha = int(155 + 100 * math.sin(tutorial_state['highlight_timer'] * math.pi / 30))
    press_space_surface = font.render("Press Space to Begin the Battle!", True, GOLD)
    press_space_surface.set_alpha(alpha)
    press_space_rect = press_space_surface.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 100))
    screen.blit(press_space_surface, press_space_rect)

def draw_title_screen():
    """Draw the game's title screen with animations"""
    global title_state
    
    # Update floating wizards
    for wizard in title_state['floating_wizards']:
        # Simple floating animation
        wizard['dy'] += math.sin(title_state['title_timer'] / 20) * 0.1
        wizard['y'] += wizard['dy']
        wizard['dy'] *= 0.95  # Damping
        
        # Draw the wizard with current color
        draw_wizard(screen, int(wizard['x']), int(wizard['y']), wizard['color'])
    
    # Draw main title "LOGOMACHY"
    title_text = "LOGOMACHY"
    base_y = WINDOW_HEIGHT // 3
    
    # Calculate total width to center the text
    total_width = 0
    letter_surfaces = []
    for i, letter in enumerate(title_text):
        # Add some vertical offset based on time and position
        offset_y = math.sin((title_state['title_timer'] + i * 5) / 10) * 10
        
        # Create shimmering color effect
        hue = (title_state['title_timer'] * 2 + i * 20) % 360
        color = pygame.Color(0, 0, 0)
        color.hsva = (hue, 80, 100, 100)
        
        letter_surface = title_large_font.render(letter, True, color)
        letter_surfaces.append((letter_surface, offset_y))
        total_width += letter_surface.get_width() + 5  # 5 pixels spacing
    
    # Draw each letter with effects
    x = (WINDOW_WIDTH - total_width) // 2
    for i, (surface, offset_y) in enumerate(letter_surfaces):
        screen.blit(surface, (x, base_y + offset_y))
        
        # Add floating particles around letters
        if random.random() < 0.2:  # 20% chance per letter per frame
            particle_color = BLUE if random.random() < 0.5 else RED
            # Create particles with random letters
            alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            selected_letter = random.choice(alphabet)
            particle = Particle(x + random.randint(0, surface.get_width()),
                              base_y + offset_y + random.randint(-20, 20),
                              particle_color,
                              selected_letter)
            particle.gravity = -0.1  # Make particles float up
            particle.vy = random.uniform(-2, -1)
            particle.vx = random.uniform(-1, 1)
            title_state['letter_particles'].append(particle)
        
        x += surface.get_width() + 5
    
    # Update and draw letter particles
    title_state['letter_particles'] = [p for p in title_state['letter_particles'] if p.is_alive()]
    for particle in title_state['letter_particles']:
        particle.update()
        particle.draw(screen)
    
    # Draw breathing "Press Space to Start" text
    if title_state['scale_increasing']:
        title_state['press_space_scale'] += 0.002
        if title_state['press_space_scale'] >= 1.1:
            title_state['scale_increasing'] = False
    else:
        title_state['press_space_scale'] -= 0.002
        if title_state['press_space_scale'] <= 0.9:
            title_state['scale_increasing'] = True
    
    press_space_text = "Press Space to Start"
    text_surface = breathing_font.render(press_space_text, True, GOLD)
    scaled_size = (int(text_surface.get_width() * title_state['press_space_scale']),
                  int(text_surface.get_height() * title_state['press_space_scale']))
    scaled_surface = pygame.transform.scale(text_surface, scaled_size)
    
    screen.blit(scaled_surface,
                ((WINDOW_WIDTH - scaled_size[0]) // 2,
                 WINDOW_HEIGHT * 2 // 3))
    
    # Update timer
    title_state['title_timer'] += 1

def reset_game():
    """Reset the game to initial state"""
    global active_player, current_input_text, active_spells, round_state
    active_player = 1
    current_input_text = ""
    active_spells.clear()
    game_state['judgments_queue'].clear()
    game_state['display_reasoning'] = None
    game_state['display_winner'] = None
    game_state['reasoning_timestamp'] = None
    game_state['judgment_history'].clear()
    game_state['paused'] = False
    game_state['game_over'] = False
    
    # Reset title screen state
    title_state['letter_particles'].clear()
    title_state['press_space_scale'] = 1.0
    title_state['scale_increasing'] = True
    title_state['title_timer'] = 0
    for wizard in title_state['floating_wizards']:
        wizard['dy'] = 0
    
    # Reset input state
    input_state['player1_text'] = ""
    input_state['player2_text'] = ""
    input_state['player1_locked'] = False
    input_state['player2_locked'] = False
    input_state['active_box'] = round_state['attacker']
    input_state['battle_phase'] = 'preparation'
    input_state['waiting_for_judgment'] = False
    input_state['attacker_locked'] = False
    input_state['defender_locked'] = False
    
    # Clear particles and wizard states
    particles.clear()
    wizard_states['player1']['exploding'] = False
    wizard_states['player1']['explosion_timer'] = 0
    wizard_states['player2']['exploding'] = False
    wizard_states['player2']['explosion_timer'] = 0

def main():
    """Main game loop"""
    global active_player, current_input_text, active_spells
    running = True
    
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if game_state['current_screen'] == 'title':
                    if event.key == pygame.K_SPACE:
                        # Transition to tutorial screen
                        game_state['current_screen'] = 'tutorial'
                        continue
                elif game_state['current_screen'] == 'tutorial':
                    if event.key == pygame.K_SPACE:
                        # Transition to game screen
                        game_state['current_screen'] = 'game'
                        reset_game()  # Start with a fresh game
                        continue
                if game_state['paused']:
                    # Handle pause menu controls
                    if event.key == pygame.K_ESCAPE:
                        # Resume game
                        game_state['paused'] = False
                    elif event.key == pygame.K_q:
                        # Show thank you screen instead of quitting
                        game_state['current_screen'] = 'thankyou'
                        game_state['paused'] = False
                    elif event.key == pygame.K_r:
                        # Restart game
                        reset_game()
                else:
                    # Handle normal game controls
                    if event.key == pygame.K_ESCAPE:
                        # Pause game and show history (always available)
                        game_state['paused'] = True
                    elif input_state['battle_phase'] == 'preparation':
                        attacker = round_state['attacker']
                        defender = round_state['defender']
                        # Only allow input for the current role
                        if not input_state['attacker_locked']:
                            # Attacker's turn
                            input_state['active_box'] = attacker
                            if event.key == pygame.K_BACKSPACE:
                                if attacker == 1 and not input_state['player1_locked']:
                                    input_state['player1_text'] = input_state['player1_text'][:-1]
                                elif attacker == 2 and not input_state['player2_locked']:
                                    input_state['player2_text'] = input_state['player2_text'][:-1]
                            elif event.key == pygame.K_RETURN:
                                # Lock attacker
                                if attacker == 1 and not input_state['player1_locked']:
                                    input_state['player1_locked'] = True
                                    input_state['attacker_locked'] = True
                                elif attacker == 2 and not input_state['player2_locked']:
                                    input_state['player2_locked'] = True
                                    input_state['attacker_locked'] = True
                                # Move to defender's turn
                                input_state['active_box'] = defender
                            else:
                                if event.unicode.isprintable():
                                    if attacker == 1 and not input_state['player1_locked']:
                                        input_state['player1_text'] += event.unicode
                                    elif attacker == 2 and not input_state['player2_locked']:
                                        input_state['player2_text'] += event.unicode
                        elif not input_state['defender_locked']:
                            # Defender's turn
                            input_state['active_box'] = defender
                            if event.key == pygame.K_BACKSPACE:
                                if defender == 1 and not input_state['player1_locked']:
                                    input_state['player1_text'] = input_state['player1_text'][:-1]
                                elif defender == 2 and not input_state['player2_locked']:
                                    input_state['player2_text'] = input_state['player2_text'][:-1]
                            elif event.key == pygame.K_RETURN:
                                # Lock defender
                                if defender == 1 and not input_state['player1_locked']:
                                    input_state['player1_locked'] = True
                                    input_state['defender_locked'] = True
                                elif defender == 2 and not input_state['player2_locked']:
                                    input_state['player2_locked'] = True
                                    input_state['defender_locked'] = True
                                # Both locked, start battle
                                if input_state['attacker_locked'] and input_state['defender_locked']:
                                    input_state['battle_phase'] = 'battle'
                                    input_state['waiting_for_judgment'] = True
                                    # Create spells for both players
                                    if input_state['player1_text'].strip():
                                        spell1 = Spell(input_state['player1_text'], (100, 450), 'right', 1)
                                        active_spells.append(spell1)
                                    if input_state['player2_text'].strip():
                                        spell2 = Spell(input_state['player2_text'], (900, 450), 'left', 2)
                                        active_spells.append(spell2)
                            else:
                                if event.unicode.isprintable():
                                    if defender == 1 and not input_state['player1_locked']:
                                        input_state['player1_text'] += event.unicode
                                    elif defender == 2 and not input_state['player2_locked']:
                                        input_state['player2_text'] += event.unicode
                    elif event.key == pygame.K_SPACE and input_state['battle_phase'] == 'result':
                        # Reconstruct broken wizards
                        if wizard_states['player1']['broken']:
                            create_wizard_reconstruction(100, 500, BLUE, wizard_states['player1'].get('reconstruction_particles', []))
                            wizard_states['player1']['broken'] = False
                        if wizard_states['player2']['broken']:
                            create_wizard_reconstruction(900, 500, RED, wizard_states['player2'].get('reconstruction_particles', []))
                            wizard_states['player2']['broken'] = False
                        # Continue to next round
                        # Swap attacker/defender
                        round_state['attacker'], round_state['defender'] = round_state['defender'], round_state['attacker']
                        input_state['battle_phase'] = 'preparation'
                        input_state['player1_text'] = ""
                        input_state['player2_text'] = ""
                        input_state['player1_locked'] = False
                        input_state['player2_locked'] = False
                        input_state['active_box'] = round_state['attacker']
                        input_state['attacker_locked'] = False
                        input_state['defender_locked'] = False
                        game_state['display_reasoning'] = None
                        game_state['display_winner'] = None
        
        # Fill the screen with dark color
        screen.fill(DARK_COLOR)
        
        if game_state['current_screen'] == 'title':
            draw_title_screen()
        elif game_state['current_screen'] == 'tutorial':
            draw_tutorial_screen()
        elif game_state['current_screen'] == 'thankyou':
            draw_thankyou_screen()
        elif game_state['paused']:
            # Draw pause screen with history
            draw_pause_screen(screen, game_state['judgment_history'])
        else:
            # Draw normal game
            # Draw wizard figures (only if not exploding or broken)
            if not wizard_states['player1']['exploding'] and not wizard_states['player1']['broken']:
                draw_wizard(screen, 100, 500, BLUE)  # Player 1 in blue
            if not wizard_states['player2']['exploding'] and not wizard_states['player2']['broken']:
                draw_wizard(screen, 900, 500, RED)   # Player 2 in red
            
            # Check for collisions between spells
            for i in range(len(active_spells)):
                for j in range(i + 1, len(active_spells)):
                    if i >= len(active_spells) or j >= len(active_spells):
                        continue  # Skip if spells were removed
                        
                    spell1 = active_spells[i]
                    spell2 = active_spells[j]
                    
                    # Check if spells collide and are from different players
                    if (spell1.rect.colliderect(spell2.rect) and 
                        spell1.player_id != spell2.player_id and 
                        spell1.state == 'flying' and 
                        spell2.state == 'flying'):
                        
                        # Set both spells to tangling state
                        spell1.state = 'tangling'
                        spell2.state = 'tangling'
                        
                        # Start judgment thread
                        threading.Thread(target=get_real_judgment, 
                                       args=(spell1.id, spell1.text, spell2.id, spell2.text)).start()
            
            # Process judgments from the queue
            if len(game_state['judgments_queue']) > 0:
                result = game_state['judgments_queue'].pop(0)
                
                # Find the spells by ID
                spell1 = None
                spell2 = None
                for spell in active_spells:
                    if spell.id == result['spell1_id']:
                        spell1 = spell
                    elif spell.id == result['spell2_id']:
                        spell2 = spell
                
                if spell1 and spell2:
                    print(f"MAD GOD'S JUDGMENT: {result['reasoning']}")
                    
                    # Store reasoning and winner for display (will stay until next collision)
                    game_state['display_reasoning'] = result['reasoning']
                    game_state['display_winner'] = result['winner']
                    game_state['reasoning_timestamp'] = time.time()
                    
                    # Add to judgment history
                    judgment_entry = {
                        'spell1_text': spell1.text,
                        'spell2_text': spell2.text,
                        'winner': result['winner'],
                        'reasoning': result['reasoning'],
                        'timestamp': time.time()
                    }
                    game_state['judgment_history'].append(judgment_entry)
                    
                    # Keep only the last 2 judgments
                    if len(game_state['judgment_history']) > 2:
                        game_state['judgment_history'].pop(0)
                    
                    # Set battle phase to result
                    input_state['battle_phase'] = 'result'
                    input_state['waiting_for_judgment'] = False
                    
                    if result['winner'] == 'PLAYER_1':
                        # Destroy Player 2 spell with explosion, set Player 1 spell back to flying
                        create_explosion_effect(spell2.pos[0], spell2.pos[1], spell2.text, RED)
                        active_spells.remove(spell2)
                        spell1.state = 'flying'
                    elif result['winner'] == 'PLAYER_2':
                        # Destroy Player 1 spell with explosion, set Player 2 spell back to flying
                        create_explosion_effect(spell1.pos[0], spell1.pos[1], spell1.text, BLUE)
                        active_spells.remove(spell1)
                        spell2.state = 'flying'
                    elif result['winner'] == 'OFFSET':
                        # Destroy both spells with explosions
                        create_explosion_effect(spell1.pos[0], spell1.pos[1], spell1.text, BLUE)
                        create_explosion_effect(spell2.pos[0], spell2.pos[1], spell2.text, RED)
                        active_spells.remove(spell1)
                        active_spells.remove(spell2)
            
            # Check for wizard hits
            check_wizard_hits()
            
            # Move and draw all active spells
            for spell in active_spells:
                spell.move()
                spell.draw(screen)
            
            # Update wizard states
            update_wizard_states()
            
            # Update and draw particles
            update_particles()
            draw_particles(screen)
            
            # Draw dual input boxes
            draw_input_boxes(screen)
            
            # Draw phase indicator
            draw_phase_indicator(screen)
            
            # Display reasoning if available (stays until next collision)
            if game_state['display_reasoning']:
                winner = game_state.get('display_winner', None)
                draw_judgment_display(screen, game_state['display_reasoning'], winner)
        
        # Update the display
        pygame.display.flip()
        
        # Control the frame rate
        clock.tick(FPS)
    
    # Quit the game
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

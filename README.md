# 🔮 Logomachy

A magical dueling game where words become spells and language is your weapon! Two wizards face off in a battle of wit and wordcraft, with their spells judged by the mysterious Mad God of Magic.

## 🌟 Features

- **Magical Duels**: Two players cast spells using creative language and descriptions
- **AI Judge**: The Mad God of Magic (powered by Google's Gemini AI) judges spell effectiveness
- **Dynamic Gameplay**: Spells collide, explode, and interact in real-time
- **Visual Effects**: Beautiful particle effects and animations bring the magic to life
- **Role Switching**: Players alternate between Attacker and Defender roles

## 🎮 How to Play

1. **Setup**: Each round, one player is the Attacker and the other is the Defender
2. **Casting**: Type your spell incantations in your respective text boxes
3. **Battle**: Watch as your spells fly across the screen and collide
4. **Judgment**: The Mad God of Magic will determine which spell prevails based on:
   - Magical Power
   - Cunning
   - Creativity
   - Effectiveness
   - Style

## 🛠️ Requirements

- Python 3.x
- Required packages:
  ```
  pygame==2.5.2
  google-generativeai==0.3.2
  python-dotenv
  ```

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/NIC397/Logomachy.git
   cd Logomachy
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root and add your Google Gemini API key:
   ```
   GEMINI_KEY=your_api_key_here
   ```

4. Run the game:
   ```bash
   python main.py
   ```

## 🎯 Controls

- Type your spell in your text box
- Press `Enter` to lock in your spell
- Press `Space` to continue to the next round
- Press `Esc` to pause/view history
- Press `Q` in the pause menu to quit
- Press `R` in the pause menu to restart

## 🎨 Game Elements

- **Blue Wizard**: Player 1
- **Red Wizard**: Player 2
- **Spell Collisions**: When spells meet, they enter a "tangling" state for judgment
- **Particle Effects**: Spells explode into colorful particles upon destruction
- **Wizard States**: Wizards can be destroyed and reconstructed through battle

## 🏆 Winning Strategy

- Be creative with your spell descriptions
- Consider both offensive and defensive strategies
- Pay attention to the Mad God's judgments to understand what it values
- Use timing and strategy when casting your spells

## License

This project is under MIT License. See [LICENSE](LICENSE) for more details.

---

*May the most eloquent wizard win!* ✨
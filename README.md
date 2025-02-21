# TeleCloneX

**TeleCloneX** is an advanced Telegram content cloning and uniqueness tool. It allows users to clone content from specified Telegram channels, including text, images, videos, and audio, and then apply various uniqueness techniques before publishing to target channels. The program operates in a multi-threaded mode, supports proxy settings for each account, and allows configurable delays.

## Features

### Cloning Modes
- **Channel History Cloning**: Copies messages from a source channel within a specified range (e.g., posts 20 to 300).
- **Real-time Cloning**: Continuously monitors a source channel for new posts and immediately clones them to the target channel.

### Account Management
- Uses **Telethon** for Telegram API interactions.
- Supports accounts in **session + JSON** format.
- Works with proxy settings in `IP:Port:Username:Password` format.

### Configuration Files
- **Sources.txt**: List of source channels to clone from.
  ```
  @source_channel
  https://t.me/source_channel
  ```
- **Targets.txt**: Target channels and the admin session responsible for posting.
  ```
  @clone_channel 380936573329
  @clone_channel1 380936784522
  ```
- **Replacements.txt**: Word replacement rules.
  ```
  Whatsapp = Telegram
  BTC = USDT
  ```

### Uniqueness Parameters
#### **Image Processing**
- Cropping (1-4 pixels)
- Brightness adjustment (1-7%)
- Contrast adjustment (1-7%)
- Rotation adjustment
- Metadata removal and replacement
- Filters and effects for imperceptible changes

#### **Video Processing**
- Hash modification
- Invisible overlay elements
- Slight frame rate adjustments
- Audio speed variation (2-4%)
- Metadata modifications

#### **Text Processing**
- **AI-based Rewriting**: Uses ChatGPT to rewrite text while maintaining structure.
- **Character Masking (RU-EN)**: Replaces Cyrillic and Latin lookalikes (e.g., `{а|a}, {О|O}, {р|p}`).

### Logging & Monitoring
- Logs all program actions.
- Records errors in a separate log file.

## Usage
1. Add source channels to `Sources.txt`.
2. Add target channels and admin accounts to `Targets.txt`.
3. Configure word replacements in `Replacements.txt`.
4. Set up image, video, and text uniqueness parameters.
5. Run TeleCloneX with the desired mode (history cloning or real-time cloning).

## Requirements
- **Python 3.8+**
- **Telethon**
- **FFmpeg** (for video processing)
- **Pillow** (for image modifications)

## Installation
```bash

python install.py
```

## Running the Program
```bash
python main.py
```

## License
This project is for educational purposes only. Use responsibly.


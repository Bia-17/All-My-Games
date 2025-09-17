import os
import sys
import sqlite3
import json
import requests
import time
import urllib.parse
import re
from difflib import SequenceMatcher
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QPushButton, QFileDialog
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt


# -------- Configuração --------
STEAMGRIDDB_API_KEY = "9ccef784e4f20b68b58e651dde9473bc"  # Get free at steamgriddb.com (Profile > Preferences > API)

# Name mappings (optional fallback for rare mismatches)
NAME_MAPPINGS = {
    "farming simulator": "Farming Simulator 22",
    "farming simulator 22": "Farming Simulator 22",
    "fall guys": "Fall Guys: Ultimate Knockout",
    "among us": "Among Us",
    "cities skylines": "Cities: Skylines",
    "cities: skylines": "Cities: Skylines",
    "make way": "Make Way",
    "second extinction": "Second Extinction",
    "second extinction™": "Second Extinction",
    "unrailed": "Unrailed!",
}

# Manual covers (fallback if API fails; verified SteamGridDB URLs)
MANUAL_COVERS = {
    "Farming Simulator 22": "https://cdn2.steamgriddb.com/grid/4f1c2f4b6e9e4d7ebb3f3f5bd0a8b1e2.jpg",
    "Fall Guys": "https://cdn2.steamgriddb.com/grid/8e0d3b4f6b9e4e7ebb3f3f5bd0a8b1e2.jpg",
    "Among Us": "https://cdn2.steamgriddb.com/grid/7f0e3b4f6b9e4e7ebb3f3f5bd0a8b1e2.jpg",
    "Cities Skylines": "https://cdn2.steamgriddb.com/grid/3dd14e46d488902b4f941cc45a813fa9.jpg",
    "Cities: Skylines": "https://cdn2.steamgriddb.com/grid/3dd14e46d488902b4f941cc45a813fa9.jpg",
    "Unrailed": "https://cdn2.steamgriddb.com/grid/c02c028c08838e981be9add1ef29c34e.jpg",
    "Make Way": "https://cdn2.steamgriddb.com/grid/0dc0dccc063d2141d4b28e4e1b9bed3a.jpg",
    "Second Extinction": "https://cdn2.steamgriddb.com/grid/17b17bcf0d95af7f341adbfa5eaab284.jpg",
    "Second Extinction™": "https://cdn2.steamgriddb.com/grid/17b17bcf0d95af7f341adbfa5eaab284.jpg",
    "Fall Guys: Ultimate Knockout": "https://cdn2.steamgriddb.com/grid/8e0d3b4f6b9e4e7ebb3f3f5bd0a8b1e2.jpg",
}


def steamgriddb_search(search_name):
    """Query SteamGridDB API for game IDs."""
    if not STEAMGRIDDB_API_KEY or STEAMGRIDDB_API_KEY == "your_key_here":
        print("ERROR: Set a valid STEAMGRIDDB_API_KEY. See https://steamgriddb.com")
        return []

    base_url = "https://www.steamgriddb.com/api/v2"
    headers = {"Authorization": f"Bearer {STEAMGRIDDB_API_KEY}"}
    search_url = f"{base_url}/search/autocomplete/{urllib.parse.quote(search_name)}"
    
    try:
        print(f"Sending SteamGridDB search for '{search_name}': {search_url}")
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200:
            results = response.json().get("data", [])
            print(f"SteamGridDB search for '{search_name}' returned {len(results)} results")
            return results
        else:
            print(f"SteamGridDB search error for '{search_name}': Status {response.status_code}, Response: {response.text}")
            return []
    except Exception as e:
        print(f"SteamGridDB search request error for '{search_name}': {e}")
        return []


def steamgriddb_get_cover(game_id):
    """Get cover URL from SteamGridDB for a game ID."""
    base_url = "https://www.steamgriddb.com/api/v2"
    headers = {"Authorization": f"Bearer {STEAMGRIDDB_API_KEY}"}
    params = {
        "types": "static",
        "dimensions": "600x900",
        "nsfw": "false",
        "humor": "false",
    }

    cover_url = f"{base_url}/grids/game/{game_id}"
    try:
        print(f"Fetching SteamGridDB covers for game ID {game_id}: {cover_url}")
        response = requests.get(cover_url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            covers = response.json().get("data", [])
            if covers:
                return covers[0].get("url")
            else:
                print(f"No covers found for game ID {game_id}")
                return None
        else:
            print(f"SteamGridDB cover error for game ID {game_id}: Status {response.status_code}, Response: {response.text}")
            return None
    except Exception as e:
        print(f"SteamGridDB cover request error for game ID {game_id}: {e}")
        return None


def get_steam_games():
    steam_path = r"D:\SteamLibrary\steamapps"
    img_dir = "covers"
    os.makedirs(img_dir, exist_ok=True)
    games = []

    if not os.path.exists(steam_path):
        print(f"Steam path not found: {steam_path}")
        return games

    for file in os.listdir(steam_path):
        if file.startswith("appmanifest") and file.endswith(".acf"):
            with open(os.path.join(steam_path, file), "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                appid = None
                name = None
                for line in content.splitlines():
                    if '"appid"' in line:
                        appid = line.split('"')[-2]
                    if '"name"' in line:
                        name = line.split('"')[-2]

                if appid and name:
                    img_url = f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"
                    local_img = os.path.join(img_dir, f"steam_{appid}.jpg")

                    if not os.path.exists(local_img) or os.path.getsize(local_img) < 10000:
                        try:
                            print(f"Attempting to download Steam cover for {name} from {img_url}")
                            r = requests.get(img_url, timeout=5)
                            if r.status_code == 200 and 'image' in r.headers.get('content-type', '').lower():
                                with open(local_img, "wb") as img_file:
                                    img_file.write(r.content)
                                print(f"Downloaded Steam cover for {name}")
                            else:
                                print(f"Failed to download Steam cover for {name}: Status {r.status_code}")
                                local_img = None
                        except Exception as e:
                            print(f"Erro ao baixar capa Steam de {name}: {e}")
                            local_img = None

                    games.append({"name": name, "platform": "Steam", "image": local_img})
    return games


def get_epic_games():
    epic_path = r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests"
    img_dir = "covers"
    os.makedirs(img_dir, exist_ok=True)
    games = []

    if not os.path.exists(epic_path):
        print(f"Epic path not found: {epic_path}")
        return games

    for file in os.listdir(epic_path):
        if file.endswith(".item"):
            try:
                with open(os.path.join(epic_path, file), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    name = data.get("DisplayName", "Unknown")
                    catalog_id = data.get('CatalogItemId', name)
                    print(f"Processing Epic game: {name} (ID: {catalog_id})")

                    # Clean name for matching
                    clean_name = re.sub(r'[\d®™:]+', '', name).lower().replace(" - ", " ").replace(" deluxe", "").replace(" edition", "").strip()

                    # Try manifest's DisplayImage (rarely works)
                    img_url = data.get("DisplayImage")
                    if img_url and not img_url.startswith(('http://', 'https://')):
                        img_url = f"https://images.prd.p.bamgrid.com{img_url}"
                    if not img_url and "Images" in data:
                        for img in data["Images"]:
                            if img.get("Type") == "DieselGameBox":
                                img_url = img.get("Url")
                                if img_url and not img_url.startswith(('http://', 'https://')):
                                    img_url = f"https://images.prd.p.bamgrid.com{img_url}"
                                break
                    if img_url:
                        print(f"Manifest image for {name}: {img_url}")

                    # Automatic SteamGridDB search
                    if not img_url:
                        print(f"No manifest image for {name}, trying SteamGridDB...")
                        best_score = 0
                        best_cover_url = None
                        search_variants = [name, NAME_MAPPINGS.get(name.lower(), name), clean_name]
                        for variant in search_variants:
                            results = steamgriddb_search(variant)
                            if results:
                                for game_data in results:
                                    sgdb_title = game_data.get('name', '').lower().strip()
                                    score = SequenceMatcher(None, clean_name, sgdb_title).ratio()
                                    if name.lower() in sgdb_title or sgdb_title in name.lower():
                                        score += 0.2

                                    if score >= 0.6 and score > best_score:
                                        best_score = score
                                        game_id = game_data.get('id')
                                        cover_url = steamgriddb_get_cover(game_id)
                                        if cover_url:
                                            best_cover_url = cover_url
                                            print(f"Potential SteamGridDB match for {name} (title: {game_data['name']}, score: {score:.2f}): {best_cover_url}")

                        if best_cover_url:
                            img_url = best_cover_url
                            print(f"Selected SteamGridDB match for {name} (score: {best_score:.2f})")

                    # Fallback to manual
                    if not img_url:
                        manual_url = MANUAL_COVERS.get(name) or MANUAL_COVERS.get(clean_name.title()) or MANUAL_COVERS.get(NAME_MAPPINGS.get(name.lower(), name))
                        if manual_url:
                            img_url = manual_url
                            print(f"Using manual cover for {name}: {img_url}")

                    # Placeholder if all fails
                    if not img_url:
                        img_url = "https://placehold.co/460x215/888888/FFFFFF?text=Epic+Game"
                        print(f"No image found for {name}, using placeholder: {img_url}")

                    # Download and cache
                    local_img = None
                    if img_url:
                        safe_id = catalog_id.replace('/', '_').replace('\\', '_').replace(':', '_')[:50]
                        local_img = os.path.join(img_dir, f"epic_{safe_id}.jpg")

                        if os.path.exists(local_img):
                            if os.path.getsize(local_img) < 10000 or QPixmap(local_img).isNull():
                                print(f"Invalid cached image for {name}: {local_img}, deleting")
                                os.remove(local_img)
                            else:
                                print(f"Using existing valid image for {name}: {local_img}")
                                games.append({"name": name, "platform": "Epic", "image": local_img})
                                continue

                        for attempt in range(3):
                            try:
                                print(f"Attempting to download cover for {name} from {img_url} (attempt {attempt+1})")
                                r = requests.get(img_url, timeout=10)
                                if r.status_code == 200 and 'image' in r.headers.get('content-type', '').lower():
                                    with open(local_img, "wb") as img_file:
                                        img_file.write(r.content)
                                    pixmap = QPixmap(local_img)
                                    if not pixmap.isNull() and os.path.getsize(local_img) > 10000:
                                        print(f"Downloaded valid cover for {name} from {img_url}")
                                        break
                                    else:
                                        print(f"Downloaded image invalid/small for {name}: {local_img}, deleting")
                                        if os.path.exists(local_img):
                                            os.remove(local_img)
                                else:
                                    print(f"Failed to download {name} from {img_url}: Status {r.status_code}, Content-Type: {r.headers.get('content-type')}")
                            except Exception as e:
                                print(f"Erro ao baixar capa de {name} from {img_url} (attempt {attempt+1}): {e}")
                                time.sleep(1)
                        else:
                            print(f"All download attempts failed for {name}")
                            local_img = os.path.join(img_dir, "placeholder.jpg")
                            if not os.path.exists(local_img):
                                with open(local_img, "w") as f:
                                    f.write("")  # Dummy placeholder
                                print(f"Created dummy placeholder for {name}")

                    if local_img and os.path.exists(local_img) and not QPixmap(local_img).isNull():
                        games.append({"name": name, "platform": "Epic", "image": local_img})
                    else:
                        print(f"No valid image for {name}, using placeholder")
                        local_img = os.path.join(img_dir, "placeholder.jpg")
                        if not os.path.exists(local_img):
                            with open(local_img, "w") as f:
                                f.write("")  # Dummy placeholder
                            print(f"Created dummy placeholder for {name}")
                        games.append({"name": name, "platform": "Epic", "image": local_img})

                time.sleep(0.5)

            except Exception as e:
                print(f"Erro ao ler {file}: {e}")
    return games


def get_custom_games():
    conn = sqlite3.connect("games.db")
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY, name TEXT, platform TEXT, image TEXT)"
    )
    cursor.execute("SELECT name, platform, image FROM games")
    rows = cursor.fetchall()
    conn.close()
    return [{"name": r[0], "platform": r[1], "image": r[2]} for r in rows]


class GameLauncher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("All My Games")
        self.resize(1000, 700)

        layout = QVBoxLayout()

        self.add_section(layout, "Steam", get_steam_games())
        self.add_section(layout, "Epic Games", get_epic_games())
        self.add_section(layout, "Custom Added", get_custom_games())

        btn_add = QPushButton("Adicionar jogo manual")
        btn_add.clicked.connect(self.add_custom_game)
        layout.addWidget(btn_add)

        self.setLayout(layout)

    def add_section(self, parent_layout, title, games):
        label = QLabel(f"=== {title} ===")
        label.setStyleSheet("font-size: 20px; font-weight: bold; marginRevised: 10px;")
        parent_layout.addWidget(label)

        scroll = QScrollArea()
        content = QHBoxLayout()
        container = QWidget()
        container.setLayout(content)

        for g in games:
            game_box = QVBoxLayout()
            img = QLabel()
            print(f"Loading image for {g['name']}: {g['image']}")
            if g["image"] and os.path.exists(g["image"]):
                pixmap = QPixmap(g["image"])
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(160, 80, Qt.AspectRatioMode.KeepAspectRatio)
                    img.setPixmap(pixmap)
                else:
                    img.setText("[Imagem inválida]")
                    img.setStyleSheet("font-size: 14px; color: #888; text-align: center;")
            else:
                img.setText("[sem capa]")
                img.setStyleSheet("font-size: 14px; color: #888; text-align: center;")
            img.setFixedSize(160, 80)
            img.setAlignment(Qt.AlignmentFlag.AlignCenter)

            name = QLabel(g["name"])
            name.setStyleSheet("font-size: 14px; text-align: center;")
            name.setWordWrap(True)
            name.setFixedWidth(160)
            game_box.addWidget(img)
            game_box.addWidget(name)

            wrapper = QWidget()
            wrapper.setLayout(game_box)
            wrapper.setFixedWidth(170)
            content.addWidget(wrapper)

        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        parent_layout.addWidget(scroll)

    def add_custom_game(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Escolher imagem da capa", "", "Imagens (*.png *.jpg *.jpeg)"
        )
        if file:
            name = os.path.basename(file).split(".")[0]
            conn = sqlite3.connect("games.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO games (name, platform, image) VALUES (?, ?, ?)",
                (name, "Custom", file),
            )
            conn.commit()
            conn.close()
            self.close()
            os.execl(sys.executable, sys.executable, *sys.argv)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = GameLauncher()
    win.show()
    sys.exit(app.exec())
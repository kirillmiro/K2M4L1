import sqlite3
from datetime import datetime
from config import DATABASE 
import os
import cv2
from PIL import Image


class DatabaseManager:
    def __init__(self, database):
        self.database = database

    def create_tables(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                user_name TEXT
            )
        ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS prizes (
                prize_id INTEGER PRIMARY KEY,
                image TEXT,
                used INTEGER DEFAULT 0
            )
        ''')

            conn.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                user_id INTEGER,
                prize_id INTEGER,
                win_time TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(prize_id) REFERENCES prizes(prize_id)
            )
        ''')

            conn.commit()

    def add_user(self, user_id, user_name):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('INSERT INTO users VALUES (?, ?)', (user_id, user_name))
            conn.commit()

    def add_prize(self, data):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.executemany('''INSERT INTO prizes (image) VALUES (?)''', data)
            conn.commit()

    def add_winner(self, user_id, prize_id):
        win_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor() 
            cur.execute("SELECT * FROM winners WHERE user_id = ? AND prize_id = ?", (user_id, prize_id))
            if cur.fetchall():
                return 0
            else:
                conn.execute('''INSERT INTO winners (user_id, prize_id, win_time) VALUES (?, ?, ?)''', (user_id, prize_id, win_time))
                conn.commit()
                return 1

    def mark_prize_used(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''UPDATE prizes SET used = 1 WHERE prize_id = ?''', (prize_id,))
            conn.commit()

    def get_users(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users")
            return [x[0] for x in cur.fetchall()] 
        
    def get_prize_img(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT image FROM prizes WHERE prize_id = ?", (prize_id,))
            return cur.fetchall()[0][0]

    def get_random_prize(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM prizes WHERE used = 0 ORDER BY random()")
            prizes = cur.fetchall()
            if not prizes:
                return None
            return prizes[0]

        
    def get_winners_count(self, prize_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM winners WHERE prize_id =?', (prize_id, ))
            return cur.fetchall()[0][0]
   
    def get_rating(self):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute('''
    SELECT users.user_name, COUNT(winners.prize_id) as count_prize FROM winners
    INNER JOIN users ON users.user_id = winners.user_id
    GROUP BY winners.user_id
    ORDER BY count_prize 
    LIMIT 10
    ''')
            return cur.fetchall()

    def get_winners_img(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cur = conn.cursor()
            cur.execute(''' 
    SELECT image FROM winners 
    INNER JOIN prizes ON 
    winners.prize_id = prizes.prize_id
    WHERE user_id = ?''', (user_id, ))
            return cur.fetchall()


def hide_img(img_name):
    image = cv2.imread(f'img/{img_name}')
    blurred_image = cv2.GaussianBlur(image, (15, 15), 0)
    pixelated_image = cv2.resize(blurred_image, (30, 30), interpolation=cv2.INTER_NEAREST)
    pixelated_image = cv2.resize(pixelated_image, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    os.makedirs("hidden_img", exist_ok=True)
    cv2.imwrite(f'hidden_img/{img_name}', pixelated_image)


def create_collage(images, output_path="collage.jpg", collage_size=(500, 500), per_row=3):
    """
    Создаёт коллаж из картинок.
    :param images: список путей к изображениям
    :param output_path: путь для сохранения результата
    :param collage_size: размер всего коллажа (ширина, высота)
    :param per_row: сколько картинок в одном ряду
    :return: путь к готовому файлу
    """
    if not images:
        return None

    collage_w, collage_h = collage_size
    rows = (len(images) + per_row - 1) // per_row
    thumb_w = collage_w // per_row
    thumb_h = collage_h // rows

    collage = Image.new("RGB", (collage_w, collage_h), color=(255, 255, 255))

    for idx, img_path in enumerate(images):
        try:
            img = Image.open(img_path)
            img = img.resize((thumb_w, thumb_h))
            x = (idx % per_row) * thumb_w
            y = (idx // per_row) * thumb_h
            collage.paste(img, (x, y))
        except Exception as e:
            print(f"Ошибка при обработке {img_path}: {e}")

    collage.save(output_path)
    return output_path


if __name__ == '__main__':
    manager = DatabaseManager(DATABASE)
    manager.create_tables()
    prizes_img = os.listdir('img')
    data = [(x,) for x in prizes_img]
    manager.add_prize(data)

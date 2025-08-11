import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
import json

DB_DIR = os.path.join("db")
os.makedirs(DB_DIR, exist_ok=True)
DATABASE_PATH = os.path.join(DB_DIR, "karaoke_songs.db")

def init_database():

    """Inicializa a base de datos creando as tablas necesarias"""

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            karaoke_filename TEXT NOT NULL,
            video_only_filename TEXT,
            vocal_filename TEXT,
            instrumental_filename TEXT,
            source_type TEXT NOT NULL,  -- 'youtube' ou 'upload'
            source_url TEXT,  -- URL de YouTube se aplica
            processing_type TEXT NOT NULL,  -- 'automatic' ou 'manual_lyrics'
            manual_lyrics TEXT,  -- Letras manuais se aplica
            language TEXT,
            enable_diarization BOOLEAN DEFAULT FALSE,
            file_size INTEGER,
            duration REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_played TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_song_to_database(song_data: Dict) -> int:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO songs (
            title, original_filename, karaoke_filename, video_only_filename,
            vocal_filename, instrumental_filename, source_type, source_url,
            processing_type, manual_lyrics, language, enable_diarization,
            file_size, duration, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        song_data.get('title'),
        song_data.get('original_filename'),
        song_data.get('karaoke_filename'),
        song_data.get('video_only_filename'),
        song_data.get('vocal_filename'),
        song_data.get('instrumental_filename'),
        song_data.get('source_type'),
        song_data.get('source_url'),
        song_data.get('processing_type'),
        song_data.get('manual_lyrics'),
        song_data.get('language'),
        song_data.get('enable_diarization', False),
        song_data.get('file_size'),
        song_data.get('duration'),
        datetime.now().isoformat()
    ))
    
    song_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return song_id

def get_all_songs() -> List[Dict]:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM songs 
        ORDER BY created_at DESC
    ''')
    
    songs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return songs

def get_song_by_id(song_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM songs WHERE id = ?', (song_id,))
    row = cursor.fetchone()
    
    song = dict(row) if row else None
    conn.close()
    
    return song

def get_song_by_filename(filename: str) -> Optional[Dict]:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM songs WHERE karaoke_filename = ?', (filename,))
    row = cursor.fetchone()
    
    song = dict(row) if row else None
    conn.close()
    
    return song

def update_last_played(song_id: int):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE songs 
        SET last_played = ? 
        WHERE id = ?
    ''', (datetime.now().isoformat(), song_id))
    
    conn.commit()
    conn.close()

def delete_song(song_id: int) -> bool:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM songs WHERE id = ?', (song_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    return deleted

def get_songs_by_search(query: str) -> List[Dict]:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM songs 
        WHERE title LIKE ? 
        ORDER BY created_at DESC
    ''', (f'%{query}%',))
    
    songs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return songs

def get_database_stats() -> Dict:
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) as total_songs FROM songs')
    total_songs = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) as automatic_songs FROM songs WHERE processing_type = "automatic"')
    automatic_songs = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) as manual_songs FROM songs WHERE processing_type = "manual_lyrics"')
    manual_songs = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) as instrumental_songs FROM songs WHERE processing_type = "instrumental"')
    instrumental_songs = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(file_size) as total_size FROM songs')
    total_size = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'total_songs': total_songs,
        'automatic_songs': automatic_songs,
        'manual_songs': manual_songs,
        'instrumental_songs': instrumental_songs,
        'total_size': total_size
    }
import sqlite3

default_db = 'C:\ProgramData\GOG.com\Galaxy\storage\galaxy-2.0.db'


def open_db():
    conn = None
    try:
        conn = sqlite3.connect(default_db)
    except Error as e:
        print(e)

    return conn


def create_master(conn=open_db()):
    cur = conn.cursor()
    cur.execute("""SELECT GamePieces.releaseKey, GamePieces.gamePieceTypeId, GamePieces.value
    FROM GameLinks
	JOIN GamePieces ON GameLinks.releaseKey = GamePieces.releaseKey""")
    return cur.fetchall()


def create_tag(conn=open_db()):
    cur = conn.cursor()
    cur.execute("""SELECT releaseKey, tag FROM UserReleaseTags""")
    return cur.fetchall()
